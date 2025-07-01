const fs = require("fs");
const { ethers } = require("hardhat");

async function main() {
    const rawData = fs.readFileSync("D:\comp codes\internship_projects\cie\StudentNFT_ver3\IgniteApp\project2\server\data\teamWallets.json");
    const accounts = JSON.parse(rawData);

    const [deployer] = await ethers.getSigners();

    const BadgeNFT = await ethers.getContractFactory("StudentBadgeNFT");
    const badgeContract = await BadgeNFT.deploy(deployer.address);
    await badgeContract.waitForDeployment(); // ✅ Ethers v6 syntax
    console.log(`Deployed to: ${badgeContract.target}`); // ✅ Use .target not .address

    for (const [name, address] of Object.entries(accounts)) {
        const tx = await deployer.sendTransaction({
            to: address,
            value: ethers.parseEther("20"), // ✅ Ethers v6
        });
        await tx.wait();
        console.log(`Sent 20 ETH to ${name} (${address})`);

        const tokenURI = `https://example.com/metadata/${name}.json`;
        const mintTx = await badgeContract.mintBadge(address, "Participation", tokenURI);
        await mintTx.wait();
        console.log(`Minted NFT to ${name} (${address})`);
    }

    console.log("✅ All accounts funded and NFTs minted.");
}

main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
});
