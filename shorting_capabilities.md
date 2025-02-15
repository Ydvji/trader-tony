class AdvancedTradingBot {
    constructor(config) {
        this.config = {
            ...config,
            shortingEnabled: true,
            maxLeverage: 5,
            platforms: {
                gmx: new GMXConnector(),
                dydx: new DydxConnector(),
                gains: new GainsConnector()
            }
        };
    }

    async setupShort(params) {
        const {
            tokenAddress,
            platform, // 'gmx', 'dydx', 'gains'
            amount,
            leverage,
            stopLoss,
            takeProfit
        } = params;

        // Verify platform supports token
        if (!await this.isPairSupported(platform, tokenAddress)) {
            throw new Error('Token not supported on selected platform');
        }

        // Risk analysis for short
        const shortAnalysis = await this.analyzeShortOpportunity(tokenAddress);
        if (!shortAnalysis.recommended) {
            console.log('⚠️ Short not recommended:', shortAnalysis.reasons);
            return shortAnalysis;
        }

        // Prepare short position
        const position = await this.prepareShortPosition({
            platform: this.config.platforms[platform],
            token: tokenAddress,
            size: amount,
            leverage: Math.min(leverage, this.config.maxLeverage),
            stopLoss,
            takeProfit
        });

        return position;
    }

    async analyzeShortOpportunity(tokenAddress) {
        // Comprehensive analysis for shorting
        const analysis = {
            recommended: false,
            reasons: [],
            metrics: {
                rugPullLikelihood: 0,
                overvaluationScore: 0,
                marketSentiment: 0
            }
        };

        // Check for rug pull signals
        const rugSignals = await this.detectRugPullSignals(tokenAddress);
        if (rugSignals.detected) {
            analysis.metrics.rugPullLikelihood = rugSignals.confidence;
            analysis.reasons.push('High rug pull probability detected');
        }

        // Analyze token metrics
        const metrics = await this.analyzeTokenMetrics(tokenAddress);
        if (metrics.overvalued) {
            analysis.metrics.overvaluationScore = metrics.overvaluationDegree;
            analysis.reasons.push('Token appears overvalued');
        }

        // Market sentiment analysis
        const sentiment = await this.analyzeSentiment(tokenAddress);
        analysis.metrics.marketSentiment = sentiment.score;

        // Make recommendation
        analysis.recommended = analysis.metrics.rugPullLikelihood > 70 ||
                             analysis.metrics.overvaluationScore > 80 ||
                             analysis.metrics.marketSentiment < 20;

        return analysis;
    }

    async executeShort(position) {
        try {
            // Get platform connector
            const platform = this.config.platforms[position.platform];

            // Open short position
            const result = await platform.openShortPosition({
                token: position.token,
                size: position.size,
                leverage: position.leverage,
                stopLoss: position.stopLoss,
                takeProfit: position.takeProfit
            });

            // Monitor position
            this.monitorShortPosition(result.positionId, platform);

            return {
                success: true,
                positionId: result.positionId,
                entryPrice: result.entryPrice,
                leverage: result.leverage,
                liquidationPrice: result.liquidationPrice
            };

        } catch (error) {
            console.error('Failed to execute short:', error);
            return {
                success: false,
                error: error.message
            };
        }
    }

    async monitorShortPosition(positionId, platform) {
        const monitor = setInterval(async () => {
            try {
                const status = await platform.getPositionStatus(positionId);
                
                // Check for take profit hit
                if (status.pnl >= status.takeProfit) {
                    await this.closeShortPosition(positionId, platform, 'TAKE_PROFIT');
                    clearInterval(monitor);
                }
                
                // Check for stop loss hit
                if (status.pnl <= -status.stopLoss) {
                    await this.closeShortPosition(positionId, platform, 'STOP_LOSS');
                    clearInterval(monitor);
                }
                
                // Check for liquidation risk
                if (status.marginRatio < 0.1) { // 10% margin remaining
                    await this.emergencyClosePosition(positionId, platform);
                    clearInterval(monitor);
                }

            } catch (error) {
                console.error('Position monitoring error:', error);
            }
        }, 1000); // Check every second
    }

    async closeShortPosition(positionId, platform, reason) {
        try {
            const result = await platform.closePosition(positionId);
            console.log(`Position closed - ${reason}:`, {
                positionId,
                pnl: result.pnl,
                reason
            });
            return result;
        } catch (error) {
            console.error('Failed to close position:', error);
            return null;
        }
    }
}

// Example usage
const tradingBot = new AdvancedTradingBot({
    // Basic configuration
    networks: ['ethereum', 'arbitrum'],
    maxLeverage: 5,
    defaultPlatform: 'gmx'
});

// Setup short position
const shortSetup = await tradingBot.setupShort({
    tokenAddress: "TOKEN_ADDRESS",
    platform: 'gmx',
    amount: 1000, // USD
    leverage: 3,
    stopLoss: 15, // 15%
    takeProfit: 50 // 50%
});

// Execute short if recommended
if (shortSetup.recommended) {
    const result = await tradingBot.executeShort(shortSetup);
    console.log('Short position opened:', result);
}