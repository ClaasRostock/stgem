import gc
from multiprocess import Process, Queue

"""
Notice that the callbacks need to understand that calls can arrive out of
order.

The result callback is called with three parameters idx, result, done. The
variable idx indicates the index of the replica that has just been completed
and the result variable contains the SUTResult corresponding to this replica.
The list done indicates what other replicas have completed before, that is,
it is a list of complete replicas without the current index.
"""

class Experiment:

    def __init__(self, N, stgem_factory, seed_factory, generator_callback=None, result_callback=None):
        self.N = N
        self.stgem_factory = stgem_factory
        self.seed_factory = seed_factory
        self.generator_callback = generator_callback
        self.result_callback = result_callback
        # This is because the CI pipeline gets a segmentation fault for calling
        # garbage collection for some reason.
        self.garbage_collect = True

    def run(self, N_workers=1, silent=False, use_gpu=True, done=None):
        if done is None:
            done = []

        if N_workers < 1:
            raise SystemExit("The number of workers must be positive.")
        elif N_workers == 1:
            # Do not use multiprocessing.
            for idx in range(self.N):
                generator = self.stgem_factory()
                seed = self.seed_factory()
                if idx not in done:
                    generator.setup(seed=seed, use_gpu=use_gpu)

                    if silent:
                        generator.logger.silent = True

                    if self.generator_callback is not None:
                        self.generator_callback(generator)

                    r = generator._run()

                    if self.result_callback is not None:
                        self.result_callback(idx, r, done)

                    done.append(idx)

                # Delete generator and force garbage collection. This is
                # especially important when using Matleb SUTs as several
                # Matlab instances take quite a lot of memory.
                del generator
                if self.garbage_collect:
                    gc.collect()
        else:
            # Use multiprocessing.
            import torch

            # Currently if CUDA is available and even if all code is run on the
            # CPU, the program will crash with a CUDA error which is due to
            # pickling and multiple initialization. This needs to be looked at,
            # but currently we just exit and instruct the user.
            if torch.cuda.is_available():
                raise SystemExit("Subprocesses are being used and these do " \
                                     "not work with any CUDA device being " \
                                     "available due to a pickling error (even in " \
                                     "the case that only CPU is requested as the " \
                                     "Pytorch device). Please disable " \
                                     "multiprocessing or set 'export " \
                                     "CUDA_VISIBLE_DEVICES=\"\"' to use CPU and " \
                                     "multiprocessing.")

            def consumer(queue_generators, queue_results, silent, generator_callback):
                while True:
                    msg = queue_generators.get()
                    if msg == "STOP": break

                    idx, generator, seed = msg

                    generator.setup(seed=seed, use_gpu=use_gpu)

                    if silent:
                        generator.logger.silent = True

                    if generator_callback is not None:
                        generator_callback(generator)

                    r = generator._run()
                    queue_results.put((idx, r))

                    # Delete and garbage collect. See above.
                    del generator
                    if self.garbage_collect:
                        gc.collect()

            def producer(queue_generators, N_workers, N, stgem_factory, seed_factory, done):
                for idx in range(N):
                    if idx not in done:
                        queue_generators.put((idx, stgem_factory(), seed_factory()))
                    else:
                        stgem_factory()
                        seed_factory()

                for _ in range(N_workers):
                    queue_generators.put("STOP")

            queue_generators = Queue(maxsize=N_workers)
            queue_results = Queue()

            # Workers that actually run generators.
            workers = []
            for _ in range(N_workers):
                consumer_process = Process(target=consumer, args=[queue_generators, queue_results, silent, self.generator_callback], daemon=True)
                workers.append(consumer_process)
                consumer_process.start()
            # A worker that hands out generators to other workers.
            producer_worker = Process(target=producer, args=[queue_generators, N_workers, self.N, self.stgem_factory, self.seed_factory, done], daemon=True)
            producer_worker.start()

            # Wait for results and process them via the callback.
            while len(done) < self.N:
                idx, r = queue_results.get()
                if self.result_callback is not None:
                    self.result_callback(idx, r, done)
                done.append(idx)

            for consumer_process in workers:
                consumer_process.join()

            producer_worker.join()

