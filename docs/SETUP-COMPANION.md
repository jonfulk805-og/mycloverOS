# CloverOS Setup Companion — Apps You Need on Your Other Computer

> **Version:** 0.1.0 (Seedling)
> **Last updated:** 2026-05-22
> **Audience:** Total beginners — no Linux or networking experience required

---

## What This Guide Is

You just installed CloverOS on a box (mini PC, NAS, server, whatever). Great.
Now you're staring at a blinking cursor or a login prompt and thinking *"...now what?"*

CloverOS is a *headless-friendly* server OS. That means most of the time you manage it
from **another computer** (your laptop, desktop, or even your phone). This guide covers
the three essential tools you need on that *other* device to set up and manage your
CloverOS box:

| # | Tool | What It Does | Cost |
|---|------|--------------|------|
| 1 | **Web Browser** | Runs the Setup Wizard, Portainer, NetMon, and all module web UIs | Free (you already have one) |
| 2 | **PuTTY** | Gives you a terminal (command line) on your CloverOS box over the network | Free |
| 3 | **Angry IP Scanner** | Finds your CloverOS box on the network and shows which ports are open | Free |

> **Mac / Linux users:** You don't need PuTTY — your built-in Terminal app has SSH.
> Angry IP Scanner works on Mac/Linux too, or you can use `nmap` from the terminal.

---

## Before You Start — What You Need

- [x] A CloverOS box that is powered on and plugged into your network (Ethernet cable recommended)
- [x] Another computer or phone on the **same network** (same Wi-Fi or same router)
- [x] About 15 minutes

---

## Tool 1: Web Browser (Setup Wizard + Web UIs)

### Why You Need It

CloverOS runs a **Setup Wizard** on first boot at port `8080`. After setup, every
module (NetMon, SentryLog, Portainer, Chappie AI, etc.) has its own web dashboard.
You access all of these from a browser — no special software required.

### What to Use

Any modern browser works:
- **Chrome** (recommended)
- **Firefox**
- **Edge**
- **Safari** (Mac/iPhone)
- **Brave**

### How to Use It

#### Step 1: Find Your CloverOS IP Address

If you have a monitor/keyboard connected to the CloverOS box, the IP address is shown
at the login screen in the welcome message:

```
⚙ mycloverOS v0.1.0 (seedling)

First-time setup? Open a browser and visit:
→ http://192.168.1.105:8080
```

If you don't have a monitor connected, use Angry IP Scanner (Tool 3 below) to find it.

#### Step 2: Open the Setup Wizard

On your other computer, open your browser and type in the address bar:

```
http://<YOUR-CLOVEROS-IP>:8080
```

For example: `http://192.168.1.105:8080`

> **The number after the colon (`:8080`) is the port number.** Think of it like an
> apartment number — the IP address is the building, and the port is which door to knock on.

Follow the wizard to set your hostname, network settings, admin credentials, and
which modules to enable.

#### Step 3: Access Module Dashboards

After the Setup Wizard finishes, here are the web addresses for each service:

| Service | URL | Port |
|---------|-----|------|
| Setup Wizard | `http://<IP>:8080` | 8080 |
| Portainer (Docker manager) | `https://<IP>:9443` | 9443 |
| NetMon (Zabbix) | `http://<IP>:8081` | 8081 |
| MyCloverVault (passwords) | `http://<IP>:8082` | 8082 |
| Chappie AI | `http://<IP>:8083` | 8083 |
| SentryLog (Graylog) | `http://<IP>:9000` | 9000 |
| CloverSign (signage) | `http://<IP>:8084` | 8084 |
| CloverGuard (web filter) | `http://<IP>:8085` | 8085 |
| CloverMedia (Jellyfin) | `http://<IP>:8096` | 8096 |
| StreamServer (Owncast) | `http://<IP>:8094` | 8094 |

> **Bookmark these!** You'll be coming back to them often.

#### Browser Security Warnings

When you visit Portainer (`https://<IP>:9443`), your browser will show a scary warning
like *"Your connection is not private"* or *"NET::ERR_CERT_AUTHORITY_INVALID"*.

**This is normal and expected.** Portainer uses a self-signed SSL certificate.

**How to get past it:**
- **Chrome/Edge:** Click *"Advanced"* → *"Proceed to \<IP\> (unsafe)"*
- **Firefox:** Click *"Advanced"* → *"Accept the Risk and Continue"*
- **Safari:** Click *"Show Details"* → *"visit this website"*

This is safe on your own local network. You're just talking to your own box.

---

## Tool 2: PuTTY (SSH Terminal Access)

### Why You Need It

Sometimes you need to type commands directly on your CloverOS box — like starting
modules, checking logs, or troubleshooting. **SSH** (Secure Shell) lets you do this
from your other computer over the network, without plugging in a monitor and keyboard.

PuTTY is the most popular free SSH client for Windows.

### Download & Install PuTTY

1. Go to: **https://www.putty.org**
2. Click **"Download PuTTY"**
3. Under **"MSI (Windows Installer)"**, download the 64-bit version
4. Run the installer — click Next through everything (defaults are fine)
5. PuTTY is now in your Start Menu

> **Mac/Linux users:** Skip PuTTY. Open your Terminal app and type:
> ```
> ssh clover@<YOUR-CLOVEROS-IP>
> ```

### Connect to CloverOS with PuTTY

#### Step 1: Launch PuTTY

Open PuTTY from your Start Menu. You'll see the PuTTY Configuration window.

#### Step 2: Enter Connection Details

| Field | What to Type |
|-------|-------------|
| **Host Name (or IP address)** | Your CloverOS IP (e.g., `192.168.1.105`) |
| **Port** | `22` |
| **Connection type** | Make sure **SSH** is selected (it's the default) |

#### Step 3: Save the Session (So You Don't Have to Type This Every Time)

1. In the **"Saved Sessions"** box, type a name: `CloverOS`
2. Click **"Save"**
3. Next time you open PuTTY, just double-click `CloverOS` in the list

#### Step 4: Click "Open"

Click the **"Open"** button at the bottom.

**First time only:** You'll see a security alert:
> *"The host key is not cached for this server..."*

Click **"Accept"** (or "Yes"). This is normal — PuTTY is just confirming it's the first
time you've connected to this machine. It won't ask again unless you reinstall CloverOS.

#### Step 5: Log In

You'll see a black terminal window:

```
login as: _
```

Type your username and press Enter:
```
login as: clover
```

Then type your password and press Enter:
```
clover@192.168.1.105's password: ********
```

> **The password won't show as you type — no dots, no stars, nothing.** This is normal
> Linux behavior. Just type it and press Enter.

If successful, you'll see the CloverOS welcome banner:

```
⚙ mycloverOS v0.1.0 (seedling)
Type 'cs-status' to see CloverStack module status

clover@cloverstack:~$
```

**You're in!** You can now type commands.

### Essential Commands to Know

```bash
# See what's running
cs-status

# Start a module
sudo cloverstack-ctl start netmon

# Stop a module
sudo cloverstack-ctl stop netmon

# Check your IP address
ip addr

# See running Docker containers
sudo docker ps

# View a module's logs
sudo docker logs netmon

# Restart a stuck container
sudo docker restart portainer

# Check disk space
df -h

# Check memory usage
free -h

# Reboot the box
sudo reboot

# Shut down the box
sudo shutdown now
```

> **Tip:** `sudo` means "run as administrator." You'll be asked for your password the
> first time you use it in a session.

### How to Restart a PuTTY Session

If your PuTTY session disconnects (network hiccup, you closed the window, the box
rebooted, etc.):

1. Open PuTTY again
2. In the **Saved Sessions** list, click `CloverOS`
3. Click **"Load"**
4. Click **"Open"**
5. Log in again with your username and password

**Or even faster:** If you saved the session, just double-click `CloverOS` in the list.

#### If PuTTY Shows "Network error: Connection refused"

This means SSH isn't running on the CloverOS box, or you have the wrong IP.

**Possible fixes:**
- Double-check the IP address (use Angry IP Scanner — Tool 3)
- If you have a monitor on the box, log in locally and run:
  ```bash
  sudo systemctl start sshd
  sudo ufw allow 22/tcp
  ```
- Make sure both devices are on the same network

#### If PuTTY Shows "Network error: Connection timed out"

- The IP address might be wrong (the box may have gotten a new one from DHCP)
- The box might be powered off
- Firewall on your Windows PC might be blocking outbound SSH

### PuTTY Pro Tips

- **Copy/Paste:** To copy text FROM PuTTY, just select it with your mouse (it auto-copies).
  To paste INTO PuTTY, right-click anywhere in the terminal window.
- **Scroll up:** Use the scrollbar on the right, or hold Shift and press Page Up.
- **Font size:** Right-click the PuTTY title bar → "Change Settings" → Window → Appearance → Font.
- **Keep-alive (prevent disconnects):** Before connecting, go to Connection → set
  "Seconds between keepalives" to `30`. Save the session.

---

## Tool 3: Angry IP Scanner (Network Discovery + Port Scanning)

### Why You Need It

When your CloverOS box boots up, it gets an IP address from your router automatically
(via DHCP). But you might not know what that address is — especially if you don't have
a monitor plugged in.

Angry IP Scanner scans your entire network and shows every device, including your
CloverOS box. It also shows which ports are open on each device — super handy for
confirming that CloverOS services are actually running and accessible.

### Download & Install

1. Go to: **https://angryip.org/download**
2. Download the Windows installer (`.exe`)
3. Run the installer — follow the prompts
4. Angry IP Scanner is now in your Start Menu

> **Requires Java:** If you don't have Java installed, Angry IP Scanner will prompt you.
> Download Java from https://www.java.com or use the bundled installer if offered.

> **Mac:** Download the Mac version from the same page. Or use `brew install angry-ip-scanner`.
>
> **Linux:** Use `nmap -sn 192.168.1.0/24` from your terminal to scan the network,
> or install Angry IP Scanner from their site.

### Find Your CloverOS Box on the Network

#### Step 1: Launch Angry IP Scanner

Open it from your Start Menu.

#### Step 2: Set the IP Range

Angry IP Scanner usually auto-detects your network range. You'll see two fields at the top:

```
IP Range: [192.168.1.1] to [192.168.1.255]
```

If your home network uses `192.168.1.x`, this is correct. Other common ranges:
- `192.168.0.1` to `192.168.0.255`
- `10.0.0.1` to `10.0.0.255`

> **How to check your range:** On your Windows computer, open Command Prompt and type
> `ipconfig`. Look for your IPv4 Address (e.g., `192.168.1.50`). The range is the first
> three numbers with `.1` to `.255` at the end.

#### Step 3: Click "Start"

Click the **Start** button (▶). The scan takes 10–30 seconds.

#### Step 4: Find CloverOS in the Results

Look for your CloverOS box in the list. Clues to identify it:

| Clue | What to Look For |
|------|-----------------|
| **Hostname** | `cloverstack` or whatever you named it |
| **MAC Vendor** | Will match your hardware (e.g., "GMKtec" for GMKTek minis) |
| **Open Ports** | Port 22 (SSH) and port 8080 (Setup Wizard) |
| **Newly appeared** | If you just plugged it in, it's the new entry |

> **Tip:** If the list is cluttered, click the column headers to sort. Sort by
> "Hostname" or "Ports" to find it faster.

### Scan for Open Ports on CloverOS

This is the power move — confirming which CloverOS services are actually running and
accessible from your network.

#### Step 1: Configure Port Scanning

1. Go to **Tools** → **Preferences** (or press Ctrl+O)
2. Click the **"Ports"** tab
3. In the **"Port Selection"** field, enter the CloverOS ports to scan:

```
22,80,443,8080,8081,8082,8083,8084,8085,8086,8087,8088,8089,8090,8094,8096,9000,9443,10051,11434
```

> **What these ports are:**
>
> | Port | Service |
> |------|---------|
> | 22 | SSH (PuTTY connects here) |
> | 80 | HTTP (Traefik) |
> | 443 | HTTPS (Traefik) |
> | 8080 | Setup Wizard / Traefik Dashboard |
> | 8081 | NetMon (Zabbix) |
> | 8082 | MyCloverVault |
> | 8083 | Chappie AI |
> | 8084 | CloverSign |
> | 8085 | CloverGuard |
> | 8086 | CloverMine |
> | 8087 | CloverPOS |
> | 8088 | CloverDesign |
> | 8089 | CloverBot |
> | 8090 | CloverMarket |
> | 8094 | StreamServer |
> | 8096 | CloverMedia |
> | 9000 | SentryLog |
> | 9443 | Portainer |
> | 10051 | Zabbix Server (agent comms) |
> | 11434 | Ollama AI Engine API |

4. Click **"OK"**

#### Step 2: Run the Scan

Click **Start** (▶) again. This time, the results will include a **Ports** column
showing which ports are open on each device.

#### Step 3: Read the Results

For your CloverOS box, you might see:

```
IP              Hostname      Ports
192.168.1.105   cloverstack   22, 8080, 9443
```

This tells you:
- ✅ Port 22 is open → SSH is running (PuTTY can connect)
- ✅ Port 8080 is open → Setup Wizard is ready
- ✅ Port 9443 is open → Portainer is running
- ❌ Port 8081 not listed → NetMon isn't started yet (use PuTTY to start it)

#### Step 4: Save Your Settings

Go to **Tools** → **Preferences** → **Ports** and make sure your port list is saved.
You can also save your scan results: **File** → **Save As** to export the list.

### Angry IP Scanner Pro Tips

- **Pin your CloverOS box:** Right-click its entry → "Add to Favorites" — it stays at
  the top of every scan.
- **Rescan just one IP:** Type the same IP in both the "from" and "to" fields to scan
  just your CloverOS box.
- **Filter alive hosts only:** Go to **Tools** → **Preferences** → **Display** →
  select *"Alive hosts (responding to ping) only"* to cut the clutter.
- **Export to CSV:** **File** → **Save As** → choose CSV format. Great for documentation.
- **Schedule regular scans:** Run a quick scan anytime you think a service might be down —
  faster than opening every URL in a browser.

---

## Putting It All Together — Your First Setup Flow

Here's the full workflow from power-on to a working CloverOS:

### 1. Power On and Connect

- Plug your CloverOS box into your router with an Ethernet cable
- Plug in the power and turn it on
- Wait 2–3 minutes for it to boot

### 2. Find It (Angry IP Scanner)

- Open Angry IP Scanner on your other computer
- Scan your network range
- Find the new device (look for `cloverstack` hostname or your hardware's MAC vendor)
- Write down the IP address

### 3. Run the Setup Wizard (Browser)

- Open Chrome/Firefox on your other computer
- Go to `http://<IP>:8080`
- Follow the wizard: set hostname, admin password, select modules
- Bookmark the address

### 4. Set Up Portainer (Browser)

- Go to `https://<IP>:9443`
- Accept the security warning
- Create your Portainer admin account *immediately* (5-minute timeout!)
- Click "Get Started"

### 5. Start Your Modules (PuTTY)

- Open PuTTY, connect to `<IP>` on port 22
- Log in as `clover`
- Start your modules:
  ```bash
  sudo cloverstack-ctl start netmon
  sudo cloverstack-ctl start sentrylog
  sudo cloverstack-ctl start myclover-vault
  sudo cloverstack-ctl start chappie
  ```
- Verify: `cs-status`

### 6. Verify Ports (Angry IP Scanner)

- Run another scan with port scanning enabled
- Confirm your module ports are now open (8081, 8082, 8083, 9000, etc.)
- Open each module's web UI in your browser to confirm

### 7. Bookmark Everything

Save these in your browser:

```
http://<IP>:8080   → Setup Wizard
https://<IP>:9443  → Portainer
http://<IP>:8081   → NetMon
http://<IP>:8082   → MyCloverVault
http://<IP>:8083   → Chappie AI
http://<IP>:9000   → SentryLog
```

---

## Glossary (For the Novice)

| Term | Plain English |
|------|---------------|
| **SSH** | Secure Shell — a way to type commands on a remote computer over the network |
| **IP Address** | The "address" of a device on your network (like `192.168.1.105`) |
| **Port** | A numbered door on a device. Each service uses a different port (like apartment numbers in a building) |
| **DHCP** | The system where your router automatically assigns IP addresses to devices |
| **Headless** | Running a computer without a monitor — you manage it over the network |
| **Terminal** | The text-based command line interface (the black window in PuTTY) |
| **`sudo`** | "Super User Do" — runs a command with administrator privileges |
| **Docker** | A system that runs apps in isolated containers (like lightweight virtual machines) |
| **Container** | A packaged app that runs inside Docker (each CloverStack module is one) |
| **Firewall** | Software that controls which network connections are allowed in and out |
| **Self-signed certificate** | An encryption certificate the server made for itself (browsers warn about it, but it's fine on your own network) |

---

## Quick Reference Card

```
╔═══════════════════════════════════════════════════════════════╗
║           CloverOS Setup — Quick Reference                    ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  FIND YOUR BOX                                                ║
║  → Angry IP Scanner: scan your network, look for              ║
║    "cloverstack" hostname or new device                       ║
║                                                               ║
║  WEB SETUP                                                    ║
║  → Browser: http://<IP>:8080                                  ║
║                                                               ║
║  SSH IN (WINDOWS)                                             ║
║  → PuTTY: Host = <IP>, Port = 22, Type = SSH                 ║
║  → Login: clover / <your password>                            ║
║                                                               ║
║  SSH IN (MAC/LINUX)                                           ║
║  → Terminal: ssh clover@<IP>                                  ║
║                                                               ║
║  CHECK STATUS                                                 ║
║  → cs-status                                                  ║
║                                                               ║
║  START MODULES                                                ║
║  → sudo cloverstack-ctl start <module>                        ║
║                                                               ║
║  KEY PORTS                                                    ║
║  22=SSH  8080=Wizard  9443=Portainer  8081=NetMon             ║
║  8082=Vault  8083=Chappie  9000=SentryLog                     ║
║                                                               ║
║  SCAN PORTS (Angry IP Scanner)                                ║
║  → Preferences > Ports > enter:                               ║
║  22,80,443,8080,8081,8082,8083,9000,9443,11434                ║
║                                                               ║
║  DOWNLOADS                                                    ║
║  → PuTTY:            https://www.putty.org                    ║
║  → Angry IP Scanner: https://angryip.org                      ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

---

## Troubleshooting

### "I can't find my CloverOS box on the network"

1. Make sure the box is powered on and the Ethernet cable is plugged in
2. Wait 2-3 minutes for it to fully boot
3. Make sure your scanning computer is on the same network
4. Try scanning a wider range (e.g., `192.168.0.1` to `192.168.1.255`)
5. Check your router's admin page for connected devices (usually at `192.168.1.1`)

### "PuTTY says 'Connection refused'"

- SSH might not be running. If you can access the web UI, that confirms the box is on.
  You'll need a monitor/keyboard to log in locally and run:
  ```bash
  sudo systemctl start sshd
  ```
- Double-check the IP address hasn't changed (rescan with Angry IP Scanner)

### "The web page won't load"

- Make sure you're using the right port number in the URL
- Try `http://` (not `https://`) for most services (except Portainer which uses `https://`)
- The module might not be started yet — SSH in and run `cs-status`
- Check if the firewall is blocking the port:
  ```bash
  sudo ufw status
  sudo ufw allow <port>/tcp
  ```

### "Portainer says it timed out"

Restart it immediately:
```bash
sudo docker restart portainer
```
Then go to `https://<IP>:9443` *right away* and create your admin account before the
5-minute window expires again.

### "My IP address keeps changing"

Your router assigns IPs dynamically (DHCP). To lock your CloverOS box to a permanent IP:

**Option A: Set a static IP on CloverOS (via PuTTY):**
```bash
sudo nano /etc/network/interfaces
```
Change `dhcp` to `static` and add your preferred address, gateway, and DNS.

**Option B: DHCP reservation on your router (recommended):**
Log into your router's admin page, find the DHCP settings, and reserve a specific IP
for your CloverOS box's MAC address. This way the router always gives it the same IP.

---

<p align="center">
  <strong>MyClover.Tech</strong> — Own Your Stack<br>
  <a href="https://myclover.tech">myclover.tech</a> · <a href="https://github.com/jonfulk805-og/mycloverOS">GitHub</a>
</p>
