# Icool song 100

## Installation

```bash
$ npm install
```

## Running the app

### Option 1: Run as Windows service (recommended for Windows)

- Create environment variables file `.env` and fill environment variables (example from `.env.example`)

```bash
$ npm run build
```

- Get absolute path of `main.js` file in folder `dist` (eg: `D:\\Deploy\\icool-song100\\dist\\main.js`)
- Update this path into script field in `node-service.js` file (eg: `script: 'D:\\Deploy\\icool-song100\\dist\\main.js'`)

```bash
$ node node-service.js
```

- Check service is running in `Services`. _If this service has **Status** is not **Running**, then **Start** or **Restart** it_
- Set this service with **Startup Type** to **Automatic**

### Option 2: Run pm2

- Fill environment variables in `ecosystem.config.js` file

```bash
$ npm run build
```

- Open Command line in root folder

```bash
$ pm2 start ecosystem.config.js
```
