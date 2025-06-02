# IDLAPS CHECKPOINT

Ada 2 Aplikasi dalam platform ini :

- Aplikasi Desktop
- Aplikasi Website

## Installation

Install IDLAPS CHECKPOINT

```bash
  klik file "PERTAMA-KALI.bat"
```

## Run Locally

APLIKASI DESKTOP

```bash
  klik file "IDLAPSCP-DESKTOP.bat"
```

APLIKASI WEBSITE

```bash
  klik file "IDLAPSCP-WEB.bat"
```

### Build .exe (pyinstaller)

`pyinstaller --noconfirm --onefile --windowed --add-data "D:/Electron/Bitbucket/electron-uhf-rc3/.env.production;." --add-data "C:/Windows/System32/libusb0.dll;."  "D:/Electron/Bitbucket/electron-uhf-rc3/main.py"`
