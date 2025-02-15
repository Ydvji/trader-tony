flowchart TD
    subgraph User Interface
        TG[Telegram Bot]
        TG --> CMD[Command Handler]
        CMD --> SNP[Snipe Command]
        CMD --> SHT[Short Command]
        CMD --> SET[Settings Command]
        CMD --> MON[Monitor Command]
    end

    subgraph Core Functionality
        SNP --> Sniper[Sniper Module]
        SHT --> Shorter[Shorter Module]
        
        Sniper --> RA[Risk Analysis]
        Shorter --> RA
        
        Sniper --> TE[Transaction Engine]
        Shorter --> TE
        
        Sniper --> PM[Position Manager]
        Shorter --> PM
    end

    subgraph Risk Analysis
        RA --> CA[Contract Analysis]
        RA --> LP[Liquidity Analysis]
        RA --> RD[Rug Detection]
        RA --> HD[Holder Distribution]
    end

    subgraph Transaction Engine
        TE --> GAS[Gas Optimizer]
        TE --> MEV[Anti-MEV]
        TE --> SL[Slippage Control]
    end

    subgraph Position Manager
        PM --> TP[Take Profit]
        PM --> SL[Stop Loss]
        PM --> TS[Trailing Stop]
        PM --> EM[Emergency Exit]
    end

    subgraph Network Layer
        ETH[Ethereum]
        SOL[Solana]
        TE --> ETH
        TE --> SOL
    end

    subgraph DEX Integration
        ETH --> UNI[Uniswap]
        SOL --> RAY[Raydium]
        ETH --> GMX[GMX]
        ETH --> DYDX[dYdX]
    end

    subgraph Monitoring
        MON --> PRC[Price Monitor]
        MON --> LIQ[Liquidity Monitor]
        MON --> VOL[Volume Monitor]
        MON --> ALT[Alert System]
    end

    subgraph Data Storage
        DB[(Database)]
        PM --> DB
        RA --> DB
        MON --> DB
    end