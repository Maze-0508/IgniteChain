from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime
import uvicorn
from web3 import Web3
import json
import os
from pathlib import Path
import re
import random
import requests
from requests_toolbelt.multipart.encoder import MultipartEncoder
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont
import qrcode
from collections import OrderedDict

load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Environment variables
contractAddress = os.getenv("SMART_CONTRACT_ADDRESS")
privateKey = os.getenv("ACCOUNT_PRIVATE_KEY")
accountAddress = os.getenv("ACCOUNT_ADDRESS")
localRPC = "http://127.0.0.1:8545"
pinataJWT = os.getenv("PINATA_JWT")
pinataBaseURL = os.getenv("PINATA_BASE_URL")
pinataLegacyURL = os.getenv("PINATA_LEGACY_URL")

# Constants
STUDENT_BADGE_DATA = "./StudentBadges/StudentBadgeData.json"
TOKENS_PER_CORRECT_ANSWER = 50
MINIMUM_TOKENS_FOR_NFT = 10
QUIZ_QUESTIONS_FILE = "quiz_questions.json"

# Initialize Web3
web3 = Web3(Web3.HTTPProvider(localRPC))
assert web3.is_connected()

# Load contract ABI
with open("D:/Internship/CIE/IgniteChain/Solidity/artifacts/contracts/StudentBadgeNFT.sol/StudentBadgeNFT.json") as f:
    abi = json.load(f)['abi']

contract = web3.eth.contract(
    address=Web3.to_checksum_address(contractAddress),
    abi=abi
)

# Quiz questions
QUIZ_QUESTIONS = [
    {
        "id": 1,
        "question": "What is intellectual property (IP)?",
        "options": [
            "A physical asset owned by a company",
            "A set of legal rights over creations of the mind",
            "A form of tangible property like land or machinery",
            "A type of government regulation on businesses"
        ],
        "correct_answer": 1
    },
    # ... (rest of your quiz questions)
]

# In-memory storage
user_sessions = {}
user_tokens = {}

# Models
class TeamMember(BaseModel):
    srn: str
    name: str
    email: str
    walletAddress: str

class TeamData(BaseModel):
    teamName: str
    idea: str
    ideaDescription: str
    captain: TeamMember
    members: List[TeamMember]
    createdAt: str

class MintRequest(BaseModel):
    badge_type: str
    token_uri: str
    recipient: str
    user_address: str

class MetadataRequest(BaseModel):
    student_name: str
    class_semester: str
    university: str
    badge_type: str
    user_address: str

class QuizAnswer(BaseModel):
    session_id: str
    answer: int

# Utility functions
def get_nonce(address):
    return web3.eth.get_transaction_count(address)

def initialize_user_tokens(user_address, initial_tokens=10000):
    if user_address not in user_tokens:
        user_tokens[user_address] = initial_tokens
    return user_tokens[user_address]

def get_user_tokens(user_address):
    return user_tokens.get(user_address, 0)

def add_tokens(user_address, amount):
    if user_address not in user_tokens:
        user_tokens[user_address] = 0
    user_tokens[user_address] += amount
    return user_tokens[user_address]

def deduct_tokens(user_address, amount):
    if user_address not in user_tokens:
        return False
    if user_tokens[user_address] < amount:
        return False
    user_tokens[user_address] -= amount
    return True

def sanitize_filename(text):
    return re.sub(r'[^\w\-]', '_', text)

# Pinata functions
async def upload_file_to_pinata(file_path: str):
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(file_path, "rb") as file_obj:
        m = MultipartEncoder(
            fields={"file": (os.path.basename(file_path), file_obj)}
        )
        headers = {
            "Authorization": f"Bearer {pinataJWT}",
            "Content-Type": m.content_type
        }
        response = requests.post(
            "https://api.pinata.cloud/pinning/pinFileToIPFS",
            headers=headers,
            data=m
        )
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="Pinata upload failed")
        return response.json()["IpfsHash"]

async def upload_metadata_to_pinata(metadata: dict):
    headers = {
        "Authorization": f"Bearer {pinataJWT}",
        "Content-Type": "application/json"
    }
    response = requests.post(
        "https://api.pinata.cloud/pinning/pinJSONToIPFS",
        json=metadata,
        headers=headers
    )
    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="Metadata upload failed")
    return response.json()["IpfsHash"]

# Certificate generation
def generate_certificate(output_file: str, name: str, team_name: str, 
                        branch: str, link: str, badge_name: str):
    base_dir = Path(__file__).parent
    font_path = base_dir / "fonts" / "dejavu-sans-webfont.ttf"
    template_path = base_dir / "certificate_of_achievement.png"

    if not font_path.exists():
        raise FileNotFoundError(f"Font not found at {font_path}")
    if not template_path.exists():
        raise FileNotFoundError("Certificate template not found")

    image = Image.open(template_path)
    draw = ImageDraw.Draw(image)
    text_color = (255, 255, 255)
    current_date = datetime.now().strftime("%B %d, %Y")

    # Fonts and positions (adjust as needed)
    name_font = ImageFont.truetype(str(font_path), 45)
    team_font = ImageFont.truetype(str(font_path), 20)
    date_font = ImageFont.truetype(str(font_path), 35)
    badge_font = ImageFont.truetype(str(font_path), 30)

    # Draw text
    draw.text((image.width//2, 680), name.title(), font=name_font, fill=text_color, anchor="mm")
    draw.text((728, 780), team_name.title(), font=team_font, fill=text_color)
    draw.text((680, 812), branch.upper(), font=team_font, fill=text_color)
    draw.text((467, 985), current_date, font=date_font, fill=text_color)
    draw.text((745, 528), badge_name, font=badge_font, fill=text_color)

    # QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(link)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color='white', back_color=(54, 151, 193))
    qr_img = qr_img.resize((250, 250))
    image.paste(qr_img, (1145, 580))

    image.save(output_file)

# Endpoints
@app.post("/initialize_user")
async def initialize_user(data: dict):
    user_address = data.get("user_address")
    if not user_address:
        raise HTTPException(status_code=400, detail="User address is required")
    tokens = initialize_user_tokens(user_address)
    return {
        "user_address": user_address,
        "tokens": tokens,
        "message": f"User initialized with {tokens} tokens"
    }

@app.get("/get_user_balance/{user_address}")
async def get_user_balance(user_address: str):
    tokens = get_user_tokens(user_address)
    return {"user_address": user_address, "tokens": tokens}

@app.post("/start_quiz")
async def start_quiz(data: dict):
    user_address = data.get("user_address")
    if not user_address:
        raise HTTPException(status_code=400, detail="User address is required")
    
    initialize_user_tokens(user_address)
    session_id = f"{user_address}_{datetime.now().timestamp()}"
    user_sessions[session_id] = {
        "user_address": user_address,
        "questions": random.sample(QUIZ_QUESTIONS, min(5, len(QUIZ_QUESTIONS))),
        "current_question": 0,
        "correct_answers": 0,
        "total_questions": min(5, len(QUIZ_QUESTIONS)),
        "started_at": datetime.now().isoformat()
    }
    return {
        "session_id": session_id,
        "total_questions": user_sessions[session_id]["total_questions"],
        "message": "Quiz session started successfully"
    }

@app.post("/submit_answer")
async def submit_answer(answer: QuizAnswer):
    session = user_sessions.get(answer.session_id)
    if not session:
        raise HTTPException(status_code=400, detail="Invalid session ID")
    
    current_q = session["questions"][session["current_question"]]
    is_correct = answer.answer == current_q["correct_answer"]
    
    if is_correct:
        session["correct_answers"] += 1
        add_tokens(session["user_address"], TOKENS_PER_CORRECT_ANSWER)
    
    session["current_question"] += 1
    quiz_completed = session["current_question"] >= len(session["questions"])
    
    response = {
        "correct": is_correct,
        "correct_answer": current_q["correct_answer"],
        "tokens_earned": TOKENS_PER_CORRECT_ANSWER if is_correct else 0,
        "total_tokens": get_user_tokens(session["user_address"]),
        "quiz_completed": quiz_completed
    }
    
    if quiz_completed:
        response.update({
            "final_score": f"{session['correct_answers']}/{session['total_questions']}",
            "total_tokens_earned": session["correct_answers"] * TOKENS_PER_CORRECT_ANSWER,
            "can_mint_nft": get_user_tokens(session["user_address"]) >= MINIMUM_TOKENS_FOR_NFT
        })
    
    return response

@app.post("/mintBadge")
async def mint_badge(request: MintRequest):
    BADGE_COST = {
        "Newbie": 10,
        "Amateur": 30,
        "Intermediate": 50,
        "Pro": 75,
        "entrePROneur": 100
    }
    
    required_tokens = BADGE_COST.get(request.badge_type)
    if not required_tokens:
        raise HTTPException(status_code=400, detail=f"Invalid badge type: {request.badge_type}")
    
    current_tokens = get_user_tokens(request.user_address)
    if current_tokens < required_tokens:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient tokens for {request.badge_type}. You have {current_tokens}, need {required_tokens}"
        )
    
    try:
        if not deduct_tokens(request.user_address, required_tokens):
            raise HTTPException(status_code=400, detail="Token deduction failed")

        nonce = get_nonce(accountAddress)
        txn = contract.functions.mintBadge(
            Web3.to_checksum_address(request.recipient),
            request.badge_type,
            request.token_uri
        ).build_transaction({
            "from": accountAddress,
            "nonce": nonce,
            "gas": 300000,
            "gasPrice": web3.to_wei("2", "gwei")
        })

        signed_txn = web3.eth.account.sign_transaction(txn, private_key=privateKey)
        tx_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)

        return {
            "tx_hash": web3.to_hex(tx_hash),
            "tokens_deducted": required_tokens,
            "remaining_tokens": get_user_tokens(request.user_address),
            "message": f"{request.badge_type} NFT minted successfully!"
        }
    except Exception as e:
        add_tokens(request.user_address, required_tokens)
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/uploadMetadata")
async def upload_metadata(data: MetadataRequest):
    try:
        base_dir = Path(__file__).parent
        generated_dir = base_dir / "generated"
        generated_dir.mkdir(exist_ok=True)
        
        output_file = generated_dir / f"certificate_{sanitize_filename(data.student_name)}_{sanitize_filename(data.badge_type)}.png"
        
        # First upload metadata with placeholder
        metadata = {
            "name": f"{data.student_name} - {data.badge_type}",
            "description": f"Certificate for {data.student_name}",
            "image": "ipfs://placeholder",
            "attributes": [
                {"trait_type": "Student", "value": data.student_name},
                {"trait_type": "Class", "value": data.class_semester},
                {"trait_type": "University", "value": data.university},
                {"trait_type": "Badge Type", "value": data.badge_type},
                {"trait_type": "Date", "value": datetime.now().strftime("%Y-%m-%d")}
            ]
        }
        
        metadata_cid = await upload_metadata_to_pinata(metadata)
        metadata_url = f"https://gateway.pinata.cloud/ipfs/{metadata_cid}"
        
        # Generate certificate with QR code
        generate_certificate(
            str(output_file),
            data.student_name,
            data.class_semester,
            data.university,
            metadata_url,
            data.badge_type
        )
        
        # Upload certificate image
        image_cid = await upload_file_to_pinata(str(output_file))
        image_url = f"https://gateway.pinata.cloud/ipfs/{image_cid}"
        
        # Update metadata with actual image URL
        metadata["image"] = f"ipfs://{image_cid}"
        metadata_cid = await upload_metadata_to_pinata(metadata)
        metadata_url = f"https://gateway.pinata.cloud/ipfs/{metadata_cid}"
        
        # Save record
        record = {
            "student_name": data.student_name,
            "class_semester": data.class_semester,
            "university": data.university,
            "badge_type": data.badge_type,
            "metadata_uri": metadata_url,
            "certificate_url": image_url,
            "user_address": data.user_address
        }
        
        if Path(STUDENT_BADGE_DATA).exists():
            with open(STUDENT_BADGE_DATA, "r") as f:
                badge_data = json.load(f)
        else:
            badge_data = []
        
        badge_data.append(record)
        with open(STUDENT_BADGE_DATA, "w") as f:
            json.dump(badge_data, f, indent=2)
        
        return {
            "metadata_uri": metadata_url,
            "certificate_url": image_url
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Admin endpoints
@app.post("/admin_add_tokens")
async def admin_add_tokens(data: dict):
    user_address = data.get("user_address")
    token_amount = data.get("token_amount")
    
    if not user_address or not token_amount:
        raise HTTPException(status_code=400, detail="User address and token amount are required")
    
    initialize_user_tokens(user_address, 0)
    new_balance = add_tokens(user_address, token_amount)
    
    return {
        "user_address": user_address,
        "tokens_added": token_amount,
        "new_balance": new_balance,
        "message": f"Added {token_amount} tokens"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "blockchain_connected": web3.is_connected(),
        "total_users": len(user_tokens)
    }

from fastapi import Path

@app.get("/teams")
async def get_teams():
    """
    Return list of unique team names (example logic based on student badge data).
    """
    if Path(STUDENT_BADGE_DATA).exists():
        with open(STUDENT_BADGE_DATA, "r") as f:
            badge_data = json.load(f)
        # Example: using "class_semester" as team name
        team_names = list({record.get("class_semester", "Unknown") for record in badge_data})
        return team_names
    else:
        # Example static fallback
        return ["Alpha Squad", "Beta Team", "Gamma Group"]

@app.get("/team_details/{team_name}")
async def get_team_details(team_name: str = Path(..., description="Name of the team")):
    """
    Return details (captain & members) for given team name.
    """
    if Path(STUDENT_BADGE_DATA).exists():
        with open(STUDENT_BADGE_DATA, "r") as f:
            badge_data = json.load(f)
        # Filter records for this team
        team_records = [r for r in badge_data if r.get("class_semester") == team_name]
        if not team_records:
            raise HTTPException(status_code=404, detail="Team not found")
        
        # Example logic: first student is captain, rest are members
        captain = team_records[0].get("student_name", "Unknown")
        members = [r.get("student_name", "Unknown") for r in team_records]

        return {
            "captain": captain,
            "members": members
        }
    else:
        # Example static fallback
        if team_name == "Alpha Squad":
            return {
                "captain": "Alice",
                "members": ["Bob", "Charlie", "David"]
            }
        else:
            raise HTTPException(status_code=404, detail="No data for this team")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)