# SDN Project Dependency and Run Guide

This guide explains what was installed in the Ubuntu VM, how it was installed, how to run the project, and what the project does. It is written so someone with very little Linux or networking experience can follow it.

## 1. What This Program Does

This project creates a small Software-Defined Networking environment.

It uses:

- Mininet to create a fake network inside one Ubuntu VM.
- Open vSwitch to act like programmable network switches.
- Ryu to run the SDN controller.
- A Zero Trust policy file to decide which hosts are allowed to talk to each other.

In simple terms, the program creates a small network with six computers. The controller checks every connection attempt and only allows traffic that matches the security policy. Traffic that is not allowed is blocked.

## 2. Use Case

This project can be used to demonstrate how Zero Trust can work in an SDN network.

Example use cases:

- A university lab project showing SDN and Zero Trust.
- A cybersecurity demo showing microsegmentation.
- A network security proof of concept.
- A controlled test environment for learning Mininet, Ryu, and OpenFlow.

## 3. What Zero Trust Is Doing

Zero Trust means the network does not automatically trust a device just because it is connected.

In this project, Zero Trust does the following:

- Checks that each host has the correct MAC address.
- Checks that each host has the correct IP address.
- Checks that each host is connected to the expected switch port.
- Allows only approved host-to-host communication.
- Blocks unknown hosts.
- Blocks traffic that violates the policy.
- Temporarily blocks suspicious hosts if they send too much traffic or scan too many ports.
- Logs allowed and denied traffic in the controller terminal.

For example:

- `h1` is allowed to talk to `h4`.
- `h3` is not allowed to talk to `h5`.
- If a host uses the wrong IP address, the controller treats it as suspicious.

## 4. Dependencies Installed in the VM

The project was set up in the VM folder:

```bash
~/SDN-clean
```

The following system packages were installed:

```bash
sudo apt update
sudo apt install -y mininet openvswitch-switch python3-pip python3-venv git nmap hping3 iperf3
```

What each dependency is for:

- `mininet`: creates the virtual network.
- `openvswitch-switch`: provides the OpenFlow switches used by Mininet.
- `python3-pip`: installs Python packages.
- `python3-venv`: creates the Python virtual environment.
- `git`: supports Git/GitHub upload and source control.
- `nmap`: can be used for scan testing.
- `hping3`: can be used for packet/attack simulation testing.
- `iperf3`: can be used for performance testing.

## 5. Python Dependencies Installed

A Python virtual environment was created:

```bash
python3 -m venv .venv
```

The project uses these Python packages:

```txt
setuptools<58
ryu==4.34
netaddr>=0.8.0
six>=1.16.0
WebOb>=1.8.0
eventlet==0.30.2
```

They were installed with:

```bash
.venv/bin/python -m pip install 'setuptools<58'
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip install 'eventlet==0.30.2'
```

The final `eventlet==0.30.2` command was needed because newer Eventlet versions are not compatible with Ryu 4.34.

## 6. Verified Installed Versions

The following checks passed in the VM:

```bash
.venv/bin/ryu-manager --version
mn --version
ovs-vsctl --version
python3 -m py_compile my_controller.py my_custom_topology.py
```

Confirmed results:

- Ryu: `ryu-manager 4.34`
- Mininet: `2.2.2`
- Open vSwitch: `2.13.8`
- Python files compiled successfully.

Mininet was also tested with:

```bash
sudo mn --test pingall
```

The result was:

```txt
0% dropped
```

That means the VM can successfully create and run a Mininet network.

## 7. How to Run the Project

Open the Ubuntu VM and open a terminal.

Go to the project folder:

```bash
cd ~/SDN-clean
```

### Step 1: Start the Controller

Run this command:

```bash
.venv/bin/ryu-manager my_controller.py
```

Leave this terminal open. This is the SDN controller. It watches the network and decides what traffic is allowed or blocked.

You should see messages showing that the controller loaded the Zero Trust policy.

### Step 2: Open a Second Terminal

Open another terminal window in the VM.

Go to the project folder again:

```bash
cd ~/SDN-clean
```

### Step 3: Start the Network

Run:

```bash
sudo python3 my_custom_topology.py
```

If Ubuntu asks for the password, type the VM password and press Enter. The password will not show while typing. That is normal.

When the network starts, you will see the Mininet prompt:

```txt
mininet>
```

### Step 4: Try Allowed Traffic

At the `mininet>` prompt, run:

```bash
h1 ping -c 3 h4
```

This should work because the policy allows `h1` to communicate with `h4`.

You can also try:

```bash
h1 ping -c 3 h2
h3 ping -c 3 h4
h4 ping -c 3 h5
h6 ping -c 3 h5
```

### Step 5: Try Blocked Traffic

At the `mininet>` prompt, run:

```bash
h3 ping -c 3 h5
```

This should fail because the Zero Trust policy does not allow `h3` to communicate with `h5`.

You can also try:

```bash
h1 ping -c 3 h5
h2 ping -c 3 h5
```

### Step 6: Watch the Controller Logs

Go back to the first terminal where the controller is running.

You should see log messages showing allowed and denied traffic.

This is the proof that the controller is enforcing the Zero Trust rules.

### Step 7: Stop the Program

In the Mininet terminal, type:

```bash
exit
```

In the controller terminal, press:

```txt
Ctrl+C
```

If Mininet ever leaves old network state behind, clean it with:

```bash
sudo mn -c
```

## 8. Simple Demo Script

For a short demo, use these commands:

Terminal 1:

```bash
cd ~/SDN-clean
.venv/bin/ryu-manager my_controller.py
```

Terminal 2:

```bash
cd ~/SDN-clean
sudo python3 my_custom_topology.py
```

Inside Mininet:

```bash
h1 ping -c 3 h4
h3 ping -c 3 h5
exit
```

Expected result:

- `h1` to `h4` should work.
- `h3` to `h5` should be blocked.
- The controller should show log messages explaining what happened.
