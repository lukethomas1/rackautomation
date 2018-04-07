from subprocess import call, DEVNULL
from time import sleep

def make_test_file(msg_name, size_kb):
    command = (
        "dd if=/dev/urandom of=" + msg_name + " bs=" +
        str(size_kb) + "k count=1"
    )
    print(command)
    call(command, shell=True, stdout=DEVNULL, stderr=DEVNULL)

def send_refactor_file(msg_name, channel, port=22124):
    command = "java -jar GvineApiClient.jar -p " + str(port) + " sendfile " + channel + \
               " " + msg_name
    print(command)
    call(command, shell=True)

if __name__ == "__main__":
    msg_index = 0
    file_size = 10
    while(True):
        msg_name = "test" + str(msg_index)
        print("Making file " + msg_name + " with size " + str(file_size) + "KB")
        make_test_file(msg_name, file_size)
        print("Sending file " + msg_name)
        send_refactor_file(msg_name, "files")
        msg_index += 1
        file_size = (file_size + 1) % 300

        sleep_time = int(file_size / 3 + 20)
        if msg_index % 30 == 0:
            sleep_time *= 3
        print("Sleeping for " + str(sleep_time) + " seconds")
        sleep(sleep_time)
        print("Done sleeping")
