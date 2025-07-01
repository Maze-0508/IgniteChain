const fs = require('fs');
const path = require('path');
require('dotenv').config();
const express = require('express');
const { MongoClient } = require('mongodb');
const cors = require('cors');
const checkForTeamDuplicates = require('./services/checkTeamDuplicates');

const app = express();
const PORT = process.env.SERVER_PORT;
const MONGO_URI = process.env.MONGO_URI;

app.use(cors({
  origin: 'http://localhost:5173',
  credentials: true
}));

app.use(express.json());

let db;

// Connect to MongoDB
MongoClient.connect(MONGO_URI, { useNewUrlParser: true, useUnifiedTopology: true })
  .then(client => {
    db = client.db('CIEIgniteDB');
    console.log('Connected to CIEIgniteDB MongoDB Atlas');
  })
  .catch(err => console.error('MongoDB connection error:', err));

/** Util: Save team name and wallet address to JSON file */
const saveTeamWalletToJson = async (teamName, walletAddress) => {
  const filePath = path.join(__dirname, 'data', 'teamWallets.json');

  let existingData = {};
  try {
    if (fs.existsSync(filePath)) {
      const fileContent = fs.readFileSync(filePath, 'utf8');
      existingData = JSON.parse(fileContent);
    }
  } catch (err) {
    console.error('Error reading JSON file:', err);
  }

  existingData[teamName] = walletAddress;

  try {
    fs.writeFileSync(filePath, JSON.stringify(existingData, null, 2));
    console.log(`Wallet info saved: ${teamName} -> ${walletAddress}`);
  } catch (err) {
    console.error('Error writing to JSON file:', err);
  }
};

// POST /add_team endpoint
app.post('/add_team', async (req, res) => {
  console.log('add_team API is called');

  try {
    const teamData = req.body;
    if (!teamData) {
      return res.status(400).json({ error: 'No Team Data Provided' });
    }

    console.log('Perform Duplicate Checks...');
    const duplicates = await checkForTeamDuplicates(db, {
      teamName: teamData.teamName,
      captain: teamData.captain,
      members: teamData.members
    });

    if (duplicates && duplicates.hasDuplicates) {
      console.log('Duplicate Email, SRN, or Team Name found');
      return res.status(409).json({
        success: false,
        message: 'Duplicate Email, SRN or Team Name found. Team not created.',
        data: duplicates
      });
    }

    console.log('No Duplicates found...');
    const result = await db.collection('teams').insertOne(teamData);

    // ✅ Save to JSON after successful DB insert
    await saveTeamWalletToJson(teamData.teamName, teamData.captain.walletAddress);

    return res.status(200).json({ 
      success: true, 
      message: 'Team successfully added.', 
      teamID: result.insertedId 
    });

  } catch (err) {
    console.error('Insert failed:', err);
    res.status(500).json({ error: 'Insert failed' });
  }
});

// Start server
app.listen(PORT, () => {
  console.log(`Server is running on http://localhost:${PORT}`);
});
