// interact.js - Script to interact with the deployed contract
const { ethers } = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
    // Load deployment info
    const deploymentPath = path.join(__dirname, "../deployments/deployment.json");

    if (!fs.existsSync(deploymentPath)) {
        console.error("❌ Deployment file not found. Please deploy the contract first.");
        process.exit(1);
    }

    const deploymentInfo = JSON.parse(fs.readFileSync(deploymentPath, 'utf8'));
    const contractAddress = deploymentInfo.contractAddress;

    console.log("🔗 Connecting to NetworkTokenWithBadges at:", contractAddress);

    // Get contract instance
    const NetworkTokenWithBadges = await ethers.getContractFactory("NetworkTokenWithBadges");
    const contract = NetworkTokenWithBadges.attach(contractAddress);

    // Get signer (deployer)
    const [deployer] = await ethers.getSigners();

    // Display current network status
    await displayNetworkStatus(contract);

    // Example interactions
    console.log("\n🎮 Example Interactions:");
    console.log("=" .repeat(50));

    // Example 1: Mint badges to nodes
    await mintExampleBadges(contract, deployer);

    // Example 2: Distribute additional tokens
    await distributeExampleTokens(contract, deployer);

    // Example 3: Query node information
    await queryNodeInformation(contract);

    console.log("\n✅ Interaction examples completed!");
}

async function displayNetworkStatus(contract) {
    console.log("\n🌐 Current Network Status:");
    console.log("=" .repeat(50));

    try {
        const totalNodes = await contract.getTotalNodes();
        const nodeNames = await contract.getAllNodeNames();
        const totalBadges = await contract.totalBadgeSupply();
        const tokenName = await contract.name();
        const tokenSymbol = await contract.symbol();

        console.log(`📊 Token: ${tokenName} (${tokenSymbol})`);
        console.log(`👥 Total Nodes: ${totalNodes}`);
        console.log(`🏆 Total Badges: ${totalBadges}`);

        console.log("\n👤 Node Details:");
        for (let i = 0; i < nodeNames.length; i++) {
            const nodeName = nodeNames[i];
            const nodeAddress = await contract.getAddressByNodeName(nodeName);
            const tokenBalance = await contract.balanceOf(nodeAddress);
            const badgeBalance = await contract.balanceOf(nodeAddress); // NFT balance

            console.log(`   ${nodeName}: ${nodeAddress}`);
            console.log(`      💰 Tokens: ${ethers.formatEther(tokenBalance)} ${await contract.symbol()}`);
            console.log(`      🏆 Badges: ${badgeBalance}`);
        }

    } catch (error) {
        console.error("❌ Error fetching network status:", error.message);
    }
}

async function mintExampleBadges(contract, signer) {
    console.log("\n🏆 Minting Example Badges:");
    console.log("-" .repeat(30));

    try {
        const nodeNames = await contract.getAllNodeNames();

        if (nodeNames.length === 0) {
            console.log("⚠️ No nodes available for badge minting");
            return;
        }

        // Mint a "Founder" badge to the first node
        const firstNode = nodeNames[0];
        console.log(`🎖️ Minting Founder badge to ${firstNode}...`);

        const tx = await contract.mintBadgeToNode(
            firstNode,
            "Founder",
            `https://example.com/metadata/founder-${firstNode}.json`
        );

        await tx.wait();
        console.log(`✅ Founder badge minted! Transaction: ${tx.hash}`);

        // If there are more nodes, mint contributor badges
        if (nodeNames.length > 1) {
            console.log(`🎖️ Minting Contributor badges to other nodes...`);

            const contributorNodes = nodeNames.slice(1, Math.min(4, nodeNames.length));
            const badgeTypes = contributorNodes.map(() => "Contributor");
            const tokenURIs = contributorNodes.map(name =>
            `https://example.com/metadata/contributor-${name}.json`
            );

            const batchTx = await contract.batchMintBadges(
                contributorNodes,
                badgeTypes,
                tokenURIs
            );

            await batchTx.wait();
            console.log(`✅ Contributor badges minted! Transaction: ${batchTx.hash}`);
        }

    } catch (error) {
        console.error("❌ Error minting badges:", error.message);
    }
}

async function distributeExampleTokens(contract, signer) {
    console.log("\n💰 Distributing Additional Tokens:");
    console.log("-" .repeat(30));

    try {
        const nodeNames = await contract.getAllNodeNames();

        if (nodeNames.length === 0) {
            console.log("⚠️ No nodes available for token distribution");
            return;
        }

        // Distribute 10 tokens to all nodes
        const additionalTokens = ethers.parseEther("10");
        console.log(`💸 Distributing 10 tokens to all ${nodeNames.length} nodes...`);

        const tx = await contract.distributeTokensToAllNodes(additionalTokens);
        await tx.wait();

        console.log(`✅ Tokens distributed! Transaction: ${tx.hash}`);

        // Distribute extra tokens to a specific node
        if (nodeNames.length > 0) {
            const bonusTokens = ethers.parseEther("5");
            const luckyNode = nodeNames[0];
            console.log(`🎁 Giving bonus 5 tokens to ${luckyNode}...`);

            const bonusTx = await contract.distributeTokensToNode(luckyNode, bonusTokens);
            await bonusTx.wait();

            console.log(`✅ Bonus tokens distributed! Transaction: ${bonusTx.hash}`);
        }

    } catch (error) {
        console.error("❌ Error distributing tokens:", error.message);
    }
}

async function queryNodeInformation(contract) {
    console.log("\n🔍 Querying Node Information:");
    console.log("-" .repeat(30));

    try {
        const nodeNames = await contract.getAllNodeNames();

        for (let i = 0; i < Math.min(3, nodeNames.length); i++) {
            const nodeName = nodeNames[i];
            const nodeAddress = await contract.getAddressByNodeName(nodeName);

            console.log(`\n📍 Node: ${nodeName} (${nodeAddress})`);

            // Get token balance
            const tokenBalance = await contract.balanceOf(nodeAddress);
            console.log(`   💰 Token Balance: ${ethers.formatEther(tokenBalance)} NET`);

            // Get badges
            try {
                const badges = await contract.getNodeBadges(nodeName);
                console.log(`   🏆 Badges: ${badges.length}`);

                if (badges.length > 0) {
                    for (let j = 0; j < badges.length; j++) {
                        const tokenURI = await contract.tokenURI(badges[j]);
                        console.log(`      Badge #${badges[j]}: ${tokenURI}`);
                    }
                }
            } catch (error) {
                console.log(`   🏆 Badges: Unable to fetch (${error.message})`);
            }
        }

        // Display badge type statistics
        console.log("\n📊 Badge Statistics:");
        const badgeTypes = ["Founder", "Contributor", "Developer", "Tester"];

        for (const badgeType of badgeTypes) {
            try {
                const minted = await contract.getMintedCount(badgeType);
                const canMint = await contract.canMintBadge(badgeType);
                console.log(`   ${badgeType}: ${minted} minted, ${canMint ? "can mint more" : "cap reached"}`);
            } catch (error) {
                console.log(`   ${badgeType}: Unable to fetch stats`);
            }
        }

    } catch (error) {
        console.error("❌ Error querying node information:", error.message);
    }
}

// Command line interface
if (require.main === module) {
    main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error("❌ Interaction failed:", error);
        process.exit(1);
    });
}

module.exports = { main, displayNetworkStatus, mintExampleBadges, distributeExampleTokens, queryNodeInformation };
