# TraderTony System Diagrams

## System Architecture

```mermaid
graph TD
    User[User] --> TG[Telegram Bot]
    TG --> Commands[Command Handler]
    TG --> Keyboard[Keyboard Interface]
    
    Commands --> WM[Wallet Manager]
    Commands --> Trading[Trading Module]
    
    WM --> Solana[Solana Network]
    Trading --> Raydium[Raydium DEX]
    Trading --> Solana
```

## Component Flow

```mermaid
graph LR
    Start[Start] --> Init[Initialize Bot]
    Init --> Listen[Listen for Commands]
    Listen --> Handle[Handle Command]
    
    Handle --> Wallet{Wallet Exists?}
    Wallet -->|No| Create[Create Wallet]
    Wallet -->|Yes| Action[Process Action]
    
    Action --> Token[Token Input]
    Action --> Balance[Balance Check]
    Action --> Trade[Trade Execution]
    
    Token --> Validate[Validate Input]
    Validate --> Fetch[Fetch Token Info]
    
    Trade --> Verify[Verify Balance]
    Verify --> Execute[Execute Trade]
```

## Data Flow

```mermaid
graph TD
    Input[User Input] --> Parse[Parse Command]
    Parse --> Validate[Validate Input]
    
    Validate -->|Token| Pool[Get Pool Data]
    Pool --> Price[Calculate Price]
    Price --> Display[Display Info]
    
    Validate -->|Trade| Balance[Check Balance]
    Balance --> Build[Build Transaction]
    Build --> Sign[Sign Transaction]
    Sign --> Send[Send Transaction]
```

## State Management

```mermaid
stateDiagram-v2
    [*] --> Idle
    Idle --> Processing: Command Received
    Processing --> TokenInfo: Token Input
    Processing --> Trading: Trade Command
    Processing --> WalletOps: Wallet Command
    
    TokenInfo --> Idle: Display Info
    Trading --> Idle: Trade Complete
    WalletOps --> Idle: Operation Complete
    
    Processing --> Error: Invalid Input
    Error --> Idle: Display Error
```

## User Interaction Flow

```mermaid
sequenceDiagram
    participant User
    participant Bot
    participant Wallet
    participant DEX
    
    User->>Bot: /start
    Bot->>Wallet: Create/Load Wallet
    Wallet-->>Bot: Wallet Info
    Bot-->>User: Welcome + Address
    
    User->>Bot: Token Input
    Bot->>DEX: Get Token Info
    DEX-->>Bot: Token Data
    Bot-->>User: Token Details
    
    User->>Bot: Buy Command
    Bot->>Wallet: Check Balance
    Wallet-->>Bot: Balance OK
    Bot->>DEX: Execute Trade
    DEX-->>Bot: Trade Result
    Bot-->>User: Confirmation
