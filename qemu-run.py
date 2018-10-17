import contextlib
import os
import sys
import subprocess
import tempfile

def create_loopback(imgfile):
    print("Creating loopback device for {}".format(imgfile))
    device = None
    try:
        r = subprocess.run(
                ("sudo", "losetup", "-f", "--show", "-P", imgfile),
                stdout=subprocess.PIPE, encoding="UTF-8")
        r.check_returncode()
        device = r.stdout.strip()
        print("Created loopback device: {}".format(device))
        return device
    except:
        remove_loopback(device)
        raise Exception("Failure creating loopback device")

def remove_loopback(device):
    assert len(device.splitlines()) == 1
    subprocess.run(("sudo", "losetup", "-d", device)).check_returncode()

def mount_boot(mount_dir, imgfile, callback):
    try:
        device = create_loopback(imgfile)
        print("Mounting {} into {}".format(device, mount_dir))
        subprocess.run(("sudo", "mount", "-o", "ro", device+"p1", mount_dir)).check_returncode()
        callback(mount_dir)
    finally:
        try:
            umount(mount_dir)
        finally:
            remove_loopback(device)

def umount(mount_dir):
    subprocess.run(("sudo", "umount", mount_dir)).check_returncode()

def extract_boot_files(workdir, imgfile):
    dest_dir = os.path.join(workdir, "boot")
    with contextlib.suppress(FileExistsError):
        os.mkdir(dest_dir)
    def copia_arquivos(mountdir):
        arquivos = (
                "kernel7.img",
                "bcm2709-rpi-2-b.dtb",
                #"cmdline.txt",
                )
        subprocess.run(("sudo", "cp",
            *(os.path.join(mountdir, a) for a in arquivos),
            dest_dir))
    with tempfile.TemporaryDirectory(dir=workdir) as mount_dir:
        mount_boot(mount_dir, imgfile, copia_arquivos)

def run_qemu(workdir, image):
    cmdline = ""
    bootdir = os.path.join(workdir, "boot")
    with open(os.path.join(bootdir, "cmdline.txt"), 'r') as cmdfile:
        cmdline = cmdfile.read()
    subprocess.run((
            "qemu-system-arm",
            "-M", "raspi2",
            "-append", cmdline,
            "-dtb", os.path.join(bootdir, "bcm2709-rpi-2-b.dtb"),
            "-kernel", os.path.join(bootdir, "kernel7.img"),
            "-serial", "stdio",
            "-sd", image,
            "-display", "none",
        )).check_returncode()

def main():
    workdir = "/tmp/qemu-exec"
    compressed_image_path = sys.argv[1]
    image_name = os.path.basename(compressed_image_path)
    if image_name.endswith(".zip"):
        image_name = image_name[0:-4]
    extracted_image_path = os.path.join(workdir, image_name + ".img")

    print("Unzipping image.")
    subprocess.run(("unzip", "-n", compressed_image_path), cwd=workdir).check_returncode()
    print("Done unzipping image.")

    extract_boot_files(workdir, extracted_image_path)

    run_qemu(workdir, extracted_image_path)
    

main()
