# Dependency and Runtime Errors Faced

This file lists the problems faced while setting up the SDN project in the Ubuntu VM, what caused them, and how they were fixed.

## 1. Project Files Were Not Yet in the VM

### Problem

The project existed on the Mac but had not been copied into the Ubuntu VM.

### Fix

A compressed archive of the project was created on the Mac and downloaded into the VM.

The first copy created a folder named:

```bash
~/SDN
```

Then a cleaner copy was created without macOS extra files, and extracted into:

```bash
~/SDN-clean
```

The clean project folder used for setup was:

```bash
cd ~/SDN-clean
```

## 2. macOS Extra Files Appeared in the First Copy

### Problem

The first archive included macOS AppleDouble files such as:

```txt
._filename
```

These are not useful for the Linux VM and could make the project folder look messy.

### Fix

A clean archive was created with macOS metadata disabled:

```bash
env COPYFILE_DISABLE=1 tar -czf /private/tmp/sdn-project-clean.tar.gz .
```

That archive was copied into the VM and extracted into:

```bash
~/SDN-clean
```

## 3. Required Linux Packages Were Missing

### Problem

The VM did not already have all tools needed to run the SDN project.

Missing or required tools included:

- Mininet
- Open vSwitch
- Python pip
- Python venv
- Git
- nmap
- hping3
- iperf3

### Fix

The following commands were used:

```bash
sudo apt update
sudo apt install -y mininet openvswitch-switch python3-pip python3-venv git nmap hping3 iperf3
```

After installation, these commands verified important tools:

```bash
mn --version
ovs-vsctl --version
```

Confirmed versions:

- Mininet: `2.2.2`
- Open vSwitch: `2.13.8`

## 4. Python Virtual Environment Was Needed

### Problem

The Ryu controller uses Python dependencies. Installing them directly into the system Python can create conflicts.

### Fix

A project-specific virtual environment was created:

```bash
cd ~/SDN-clean
python3 -m venv .venv
```

The virtual environment Python was then used for package installation:

```bash
.venv/bin/python -m pip install -r requirements.txt
```

## 5. Ryu Install Failed with Modern Setuptools

### Problem

The first Ryu install failed with an error similar to:

```txt
AttributeError: module 'setuptools.command.easy_install' has no attribute 'get_script_args'
```

### Cause

Ryu 4.34 is an older package. It is not fully compatible with newer versions of `setuptools`.

### Fix

`setuptools` was downgraded inside the virtual environment:

```bash
.venv/bin/python -m pip install 'setuptools<58'
```

Then the dependency install was retried:

```bash
.venv/bin/python -m pip install -r requirements.txt
```

The project `requirements.txt` was also updated to include:

```txt
setuptools<58
```

## 6. Ryu Installed but Failed to Start Because of Eventlet

### Problem

After Ryu installed, this command failed:

```bash
.venv/bin/ryu-manager --version
```

The error was:

```txt
ImportError: cannot import name 'ALREADY_HANDLED' from 'eventlet.wsgi'
```

### Cause

Ryu 4.34 expects an older Eventlet API. The first install pulled a newer Eventlet version that removed or changed the symbol Ryu expected.

### Fix

Eventlet was pinned to a compatible version:

```bash
sed -i 's/eventlet>=0.30.2/eventlet==0.30.2/' requirements.txt
.venv/bin/python -m pip install 'eventlet==0.30.2'
```

This also installed a compatible `dnspython` version:

```txt
dnspython-1.16.0
eventlet-0.30.2
```

After that, Ryu worked:

```bash
.venv/bin/ryu-manager --version
```

Result:

```txt
ryu-manager 4.34
```

The project `requirements.txt` was also updated to include:

```txt
eventlet==0.30.2
```

## 7. Controller Startup Needed a Smoke Test

### Problem

Installing dependencies is not enough. The controller also needed to be tested to make sure the project code could load.

### Fix

The controller was started for a short test:

```bash
timeout 5 .venv/bin/ryu-manager my_controller.py
```

Successful output included:

```txt
loading app my_controller.py
instantiating app my_controller.py of ZeroTrustController
Loaded 6 Zero Trust hosts and 20 policy pairs
```

This confirmed that Ryu could load the controller and read the policy.

## 8. Python Syntax Needed Verification

### Problem

After editing the controller and topology files, the Python files needed to be checked for syntax errors.

### Fix

The files were compiled:

```bash
python3 -m py_compile my_controller.py my_custom_topology.py
```

There was no error output, which means the files compiled successfully.

## 9. Mininet Needed a Runtime Test

### Problem

Even if Mininet is installed, it still needs root privileges and working Open vSwitch support to create a network.

### Fix

A Mininet test was run:

```bash
sudo mn --test pingall
```

Successful result:

```txt
*** Results: 0% dropped (2/2 received)
*** Done
```

This confirmed that Mininet and Open vSwitch work inside the VM.

## 10. Commands Typed into the VM Could Be Mangled

### Problem

Some long commands typed into the VM through the remote control interface could become unreliable or awkward.

### Fix

Short commands were used one at a time. This made setup more reliable.

Example:

```bash
cd ~/SDN-clean
python3 -m venv .venv
.venv/bin/python -m pip install 'setuptools<58'
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip install 'eventlet==0.30.2'
```

## 11. Password Prompt During Sudo

### Problem

Some commands required administrator permission, especially package installation and Mininet commands.

Examples:

```bash
sudo apt install -y mininet openvswitch-switch python3-pip python3-venv git nmap hping3 iperf3
sudo python3 my_custom_topology.py
sudo mn --test pingall
```

### Fix

The VM user entered the sudo password when prompted. The password did not show on screen while typing, which is normal for Linux.

After sudo was authenticated, later sudo commands could run without asking for the password again for a short time.

## 12. Final Working Setup

The final working setup uses:

```txt
Ubuntu VM project folder: ~/SDN-clean
Python virtual environment: ~/SDN-clean/.venv
Ryu version: 4.34
Mininet version: 2.2.2
Open vSwitch version: 2.13.8
Eventlet version: 0.30.2
Setuptools version: below 58
```

The final commands used to verify the project were:

```bash
cd ~/SDN-clean
.venv/bin/ryu-manager --version
python3 -m py_compile my_controller.py my_custom_topology.py
timeout 5 .venv/bin/ryu-manager my_controller.py
sudo mn --test pingall
```

All of these checks passed after applying the dependency fixes.
