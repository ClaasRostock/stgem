import numpy as np

def generate_odroid_data(data_file):
    """
    This function loads the Odroid data from CSV, converts it to appropriate
    form, and saves it to a Numpy .npy file.
    """

    """
    Data format:
    <configuration name>,<power>,<performance>,<efficiency>

    The configuration name is a string with 5 parts separated by / which
    correspond to input parameters. An example is

    4a7/1100Mhz/100%3a15/800Mhz/100%

    The parts 2,4,5 are used as such by removing 'Mhz' and '%'. The first part is
    mapped to an integer in order of appearance, and so is the segment of the
    third part after '%'. This gives a total 6 input parameters. The above line
    maps to

    0,1100,100,1,800,100
    """

    # This function returns encodings of strings to integers.
    encoding = {}

    def encode(s):
        if s not in encoding:
            encoding[s] = 0 if not encoding else max(encoding.values()) + 1
        return encoding[s]

    data = []
    with open(data_file, mode="r") as f:
        c = 0
        skip = 1
        while True:
            line = f.readline()
            if line == "":
                break
            c += 1
            if c <= skip:
                continue

            pcs = line.split(",")
            w = pcs[0].split("/")
            if len(w) < 5:
                print("Line {} malformed: {}".format(c, line))
                continue

            new = []
            # Test input variables.
            new.append(encode(w[0]))
            new.append(int(w[1][:-3]))
            w2 = w[2].split("%")
            new.append(int(w2[0]))
            new.append(encode(w2[1]))
            new.append(int(w[3][:-3]))
            new.append(int(w[4][:-1]))
            # Test outputs.
            new.append(float(pcs[1]))
            new.append(float(pcs[2]))
            new.append(float(pcs[3]))

            data.append(new)

    np.save(f"{data_file[:-4]}.npy", data)
