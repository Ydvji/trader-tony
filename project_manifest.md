{
    "name": "trader-tony",
    "version": "1.0.0",
    "description": "Advanced trading bot with sniping and shorting capabilities",
    "main": "src/index.js",
    "scripts": {
        "start": "node src/index.js",
        "dev": "nodemon src/index.js",
        "test": "jest",
        "lint": "eslint src/"
    },
    "dependencies": {
        "node-telegram-bot-api": "^0.61.0",
        "@solana/web3.js": "^1.87.0",
        "ethers": "^5.7.2",
        "web3": "^1.9.0",
        "axios": "^1.3.4",
        "dotenv": "^16.0.3",
        "winston": "^3.8.2",
        "mongoose": "^7.0.3",
        "express": "^4.18.2"
    },
    "devDependencies": {
        "jest": "^29.5.0",
        "eslint": "^8.36.0",
        "nodemon": "^2.0.22",
        "prettier": "^2.8.7"
    },
    "repository": {
        "type": "git",
        "url": "git+https://github.com/yourusername/advanced-trading-bot.git"
    },
    "keywords": [
        "trading",
        "bot",
        "crypto",
        "sniper",
        "defi"
    ],
    "author": "Your Name",
    "license": "MIT",
    "bugs": {
        "url": "https://github.com/yourusername/advanced-trading-bot/issues"
    },
    "homepage": "https://github.com/yourusername/advanced-trading-bot#readme"
}