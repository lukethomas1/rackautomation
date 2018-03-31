from subprocess import call
from time import sleep

def make_test_file(msg_name, size_kb):
    command = (
        "dd if=/dev/urandom of=" + msg_name + " bs=" +
        str(size_kb) + "k count=1"
    )
    call(command, shell=True)

def send_refactor_file(msg_name, channel, port=22124):
    command += " && java -jar GvineApiClient.jar -p " + str(port) + " sendfile " + channel + \
               " " + msg_name
    call(command, shell=True)

if __name__ == "__main__":
    msg_index = 0
    file_size = 10
    while(True):
        msg_name = "test" + str(msg_index)
        make_test_file(msg_name, file_size)
        send_refactor_file(msg_name, "files")
        msg_index += 1
        file_size = (file_size + 1) % 300

        sleep_time = int(file_size / 3)
        sleep(sleep_time)
