from flask import Flask, jsonify, request
import requests
from web3 import Web3
import json
import os
from dotenv import load_dotenv
from datetime import datetime
from requests_toolbelt.multipart.encoder import MultipartEncoder
from pathlib import Path
from collections import OrderedDict
import pyshorteners
import random
import re
load_dotenv()

# Environment variables
contractAddress = os.getenv("SMART_CONTRACT_ADDRESS")
privateKey = os.getenv("ACCOUNT_PRIVATE_KEY")
accountAddress = os.getenv("ACCOUNT_ADDRESS")
localRPC = "http://127.0.0.1:8545"

# Contract and Pinata configuration
contractJSON = r"D:\comp codes\internship_projects\cie\StudentNFT_ver3\IgniteApp\Solidity\artifacts\contracts\StudentBadgeNFT.sol\StudentBadgeNFT.json"
pinataJWT = os.getenv("PINATA_JWT")
pinataBaseURL = os.getenv("PINATA_BASE_URL")
pinataLegacyURL = os.getenv("PINATA_LEGACY_URL")
STUDENT_BADGE_DATA = "./StudentBadges/StudentBadgeData.json"
CERTIFICATE_DIR = ""

# Quiz configuration
TOKENS_PER_CORRECT_ANSWER = 50
MINIMUM_TOKENS_FOR_NFT = 10
QUIZ_QUESTIONS_FILE = "quiz_questions.json"

# Pinata Headers
PINATA_JWT = os.getenv("PINATA_JWT")
HEADERS = {
    "Authorization": f"Bearer {PINATA_JWT}"
}

# Initialize Flask app
app = Flask(__name__)

# Connect to blockchain
web3 = Web3(Web3.HTTPProvider(localRPC))
assert web3.is_connected()

# Load contract ABI
with open(contractJSON) as f:
    abi = json.load(f)['abi']

checksum_address = Web3.to_checksum_address(contractAddress)
contract = web3.eth.contract(address=checksum_address, abi=abi)

# Quiz questions (hardcoded for now, can be loaded from JSON file)
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
    {
        "id": 2,
        "question": "Which of the following is NOT a type of intellectual property?",
        "options": [
            "Patents",
            "Copyrights",
            "Trademarks",
            "Having a thought for an idea for a smartphone"
        ],
        "correct_answer": 3
    },
    {
        "id": 3,
        "question": "What type of intellectual property protects an invention?",
        "options": [
            "Copyright",
            "Trademark",
            "Patent",
            "Trade secret"
        ],
        "correct_answer": 2
    },
    {
        "id": 4,
        "question": "A trademark primarily protects:",
        "options": [
            "Literary and artistic works",
            "A company's brand name, logo, or slogan",
            "The design of a product",
            "A new technological invention"
        ],
        "correct_answer": 1
    },
    {
        "id": 5,
        "question": "How long does a copyright generally last in most countries?",
        "options": [
            "10 years",
            "The lifetime of the author plus 60-70 years",
            "20 years from the filing date",
            "Indefinitely as long as it is in use"
        ],
        "correct_answer": 1
    }
]

# In-memory storage for user sessions and tokens
user_sessions = {}
user_tokens = {}

# Utility functions
def get_nonce(address):
    return web3.eth.get_transaction_count(address)

def initialize_user_tokens(user_address, initial_tokens=10000):
    """Initialize user with tokens if not already present"""
    if user_address not in user_tokens:
        user_tokens[user_address] = initial_tokens
    return user_tokens[user_address]

def get_user_tokens(user_address):
    """Get current token balance for user"""
    return user_tokens.get(user_address, 0)

def add_tokens(user_address, amount):
    """Add tokens to user balance"""
    if user_address not in user_tokens:
        user_tokens[user_address] = 0
    user_tokens[user_address] += amount
    return user_tokens[user_address]

def deduct_tokens(user_address, amount):
    """Deduct tokens from user balance"""
    if user_address not in user_tokens:
        return False
    if user_tokens[user_address] < amount:
        return False
    user_tokens[user_address] -= amount
    return True


def uploadFileToPinata(filePath):
    print(f"Checking file path: {filePath}")
    filePath = filePath.strip()

    if not os.path.isfile(filePath):
        raise FileNotFoundError(f"File not found: {filePath}")

    fileName = os.path.basename(filePath)
    print(f"The fileName is: {fileName}")

    with open(filePath, "rb") as fileObj:
        m = MultipartEncoder(
            fields={
                "file": (fileName, fileObj, "application/octet-stream")
            }
        )

        headers = {
            "Authorization": f"Bearer {PINATA_JWT}",
            "Content-Type": m.content_type
        }

        response = requests.post(
            "https://uploads.pinata.cloud/v3/files",
            headers=headers,
            data=m,
            timeout=30
        )

        if response.status_code != 200:
            print("❌ Metadata upload failed:")
            print("Status Code:", response.status_code)
            print("Response:", response.text)
            raise requests.HTTPError(f"Upload failed: {response.status_code} - {response.text}")

        responseJSON = response.json()

        if "data" not in responseJSON or "cid" not in responseJSON["data"]:
            raise ValueError("Unexpected response format: 'cid' missing")

        return responseJSON["data"]


def uploadMetadataToPinata(metadata):
    url = pinataLegacyURL
    headers = {
        "Authorization": f"Bearer {pinataJWT}",
        "Content-Type": "application/json"
    }
    response = requests.request("POST", url, json=metadata, headers=headers)
    if response.status_code != 200:
        raise requests.HTTPError(f"Pinning Metadata to Pinata Failed: {response.status_code} - {response.text}")

    responseJSON = response.json()
    if "IpfsHash" not in responseJSON:
        raise ValueError("IPFSHash is not found in the Response")
    return responseJSON["IpfsHash"]

def generate_certificate(output_file, name, team_name, branch, link, badge_name):
    """
    Generate a certificate with the provided details.
    """
    from PIL import Image, ImageDraw, ImageFont
    from datetime import datetime
    import qrcode
    import os
    baseDir = os.path.dirname(os.path.abspath(__file__))
    font_file = os.path.join(baseDir, "fonts", "dejavu-sans-webfont.ttf")
    name_font = ImageFont.truetype(font_file, 45)

    # Use a Linux system font
    #font_file = "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-Bold.ttf"
    #try:
    #    font_file = "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"
    #    name_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 45)
    #except OSError:
    #    raise FileNotFoundError(f"Font not found at: {font_file}. Install with: sudo dnf install dejavu-sans-fonts")
#
#    if not os.path.exists(font_file):
#        raise FileNotFoundError("Font file not found at expected Linux path")
#
#    # Use the Linux-friendly path for the certificate template
    input_file = os.path.join(baseDir, "certificate_of_achievement.png")
    if not os.path.exists(input_file):
        raise FileNotFoundError("Certificate template image not found!")

    # Open base certificate
    image = Image.open(input_file)
    draw = ImageDraw.Draw(image)

    # Text color
    text_color = (255, 255, 255)

    # Get current date
    current_date = datetime.now().strftime("%B %d, %Y")

    # Adjust font sizes to fit
    name_font = ImageFont.truetype(font_file, 45)
    team_name_font = ImageFont.truetype(font_file, 20)
    branch_font = ImageFont.truetype(font_file, 20)
    date_font = ImageFont.truetype(font_file, 35)
    badge_font = ImageFont.truetype(font_file, 30)


    # Text positions
    name_position =((image.width - draw.textbbox((0, 0), name, font=name_font)[2]) // 2, 680)
    team_name_position =(728, 780)
    branch_position =(680, 812)
    date_position = (467, 985)
    badge_name_position = (745, 528)

    # Now draw the text
    draw.text(name_position, name.title(), font=name_font, fill=text_color)
    draw.text(team_name_position, team_name.title(), font=team_name_font, fill=text_color)
    draw.text(branch_position, branch.upper(), font=branch_font, fill=text_color)
    draw.text(date_position, current_date, font=date_font, fill=text_color)
    draw.text(badge_name_position, badge_name, font=badge_font, fill=text_color)

    # Generate QR code with a custom color
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(link)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color='white', back_color=(54, 151, 193))

    # Resize QR code if needed
    qr_img = qr_img.resize((250, 250))

    # Define QR code position
    qr_position = (1145, 580)

    # Paste QR code into certificate
    image.paste(qr_img, qr_position)

    # Save the updated image
    image.save(output_file)
def sanitize_filename(text):
    # Replace any character that is not alphanumeric or underscore with underscore
    return re.sub(r'[^\w\-]', '_', text)

def test_upload_to_pinata(file_path):
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    print("Uploading:", file_path)
    file_size = os.path.getsize(file_path)
    print("File size:", file_size)

    if file_size == 0:
        raise ValueError("File is empty!")

    with open(file_path, "rb") as file_obj:
        m = MultipartEncoder(
            fields={
                "file": (os.path.basename(file_path), file_obj, "application/octet-stream"),
                "network": "public"
            }
        )

        headers = {
            "Authorization": f"Bearer {PINATA_JWT}",  # Make sure this is set
            "Content-Type": m.content_type
        }

        response = requests.post(
            "https://uploads.pinata.cloud/v3/files",
            headers=headers,
            data=m
        )

        print("Response:", response.status_code)
        print("Body:", response.text)

        if response.status_code != 200:
            raise requests.HTTPError(f"Upload failed: {response.status_code} - {response.text}")

        res_json = response.json()
        if "data" not in res_json or "cid" not in res_json["data"]:
            raise ValueError("Unexpected response format: 'cid' missing")

        return {
            "cid": res_json["data"]["cid"],
            "url": f"https://gateway.pinata.cloud/ipfs/{res_json['data']['cid']}"
        }
# NEW QUIZ-RELATED ENDPOINTS

@app.route("/initialize_user", methods=["POST"])
def initialize_user():
    """Initialize a new user with starting tokens"""
    data = request.get_json()
    user_address = data.get("user_address")

    if not user_address:
        return jsonify({"error": "User address is required"}), 400

    tokens = initialize_user_tokens(user_address)
    return jsonify({
        "user_address": user_address,
        "tokens": tokens,
        "message": f"User initialized with {tokens} tokens"
    })

@app.route("/get_user_balance/<user_address>", methods=["GET"])
def get_user_balance(user_address):
    """Get current token balance for a user"""
    tokens = get_user_tokens(user_address)
    return jsonify({
        "user_address": user_address,
        "tokens": tokens
    })

@app.route("/start_quiz", methods=["POST"])
def start_quiz():
    """Start a new quiz session for a user"""
    data = request.get_json()
    user_address = data.get("user_address")

    if not user_address:
        return jsonify({"error": "User address is required"}), 400

    # Initialize user if not exists
    initialize_user_tokens(user_address)

    # Create quiz session
    session_id = f"{user_address}_{datetime.now().timestamp()}"
    user_sessions[session_id] = {
        "user_address": user_address,
        "questions": random.sample(QUIZ_QUESTIONS, min(5, len(QUIZ_QUESTIONS))),
        "current_question": 0,
        "correct_answers": 0,
        "total_questions": min(5, len(QUIZ_QUESTIONS)),
        "started_at": datetime.now().isoformat()
    }

    return jsonify({
        "session_id": session_id,
        "total_questions": user_sessions[session_id]["total_questions"],
        "message": "Quiz session started successfully"
    })

@app.route("/get_question/<session_id>", methods=["GET"])
def get_question(session_id):
    """Get current question for a quiz session"""
    if session_id not in user_sessions:
        return jsonify({"error": "Invalid session ID"}), 400

    session = user_sessions[session_id]

    if session["current_question"] >= len(session["questions"]):
        return jsonify({"error": "Quiz completed"}), 400

    current_q = session["questions"][session["current_question"]]

    return jsonify({
        "question_number": session["current_question"] + 1,
        "total_questions": session["total_questions"],
        "question": current_q["question"],
        "options": current_q["options"]
    })

@app.route("/submit_answer", methods=["POST"])
def submit_answer():
    """Submit answer for current question"""
    data = request.get_json()
    session_id = data.get("session_id")
    answer = data.get("answer")  # 0-based index

    if session_id not in user_sessions:
        return jsonify({"error": "Invalid session ID"}), 400

    if answer is None:
        return jsonify({"error": "Answer is required"}), 400

    session = user_sessions[session_id]
    current_q = session["questions"][session["current_question"]]

    is_correct = answer == current_q["correct_answer"]
    tokens_earned = 0

    if is_correct:
        session["correct_answers"] += 1
        tokens_earned = TOKENS_PER_CORRECT_ANSWER
        add_tokens(session["user_address"], tokens_earned)

    session["current_question"] += 1

    # Check if quiz is completed
    quiz_completed = session["current_question"] >= len(session["questions"])

    response = {
        "correct": is_correct,
        "correct_answer": current_q["correct_answer"],
        "tokens_earned": tokens_earned,
        "total_tokens": get_user_tokens(session["user_address"]),
        "quiz_completed": quiz_completed
    }

    if quiz_completed:
        response.update({
            "final_score": f"{session['correct_answers']}/{session['total_questions']}",
            "total_tokens_earned": session["correct_answers"] * TOKENS_PER_CORRECT_ANSWER,
            "can_mint_nft": get_user_tokens(session["user_address"]) >= MINIMUM_TOKENS_FOR_NFT
        })

    return jsonify(response)

@app.route("/quiz_summary/<session_id>", methods=["GET"])
def quiz_summary(session_id):
    """Get quiz session summary"""
    if session_id not in user_sessions:
        return jsonify({"error": "Invalid session ID"}), 400

    session = user_sessions[session_id]
    user_address = session["user_address"]
    current_tokens = get_user_tokens(user_address)

    return jsonify({
        "session_id": session_id,
        "user_address": user_address,
        "correct_answers": session["correct_answers"],
        "total_questions": session["total_questions"],
        "tokens_earned": session["correct_answers"] * TOKENS_PER_CORRECT_ANSWER,
        "current_total_tokens": current_tokens,
        "can_mint_nft": current_tokens >= MINIMUM_TOKENS_FOR_NFT,
        "tokens_needed_for_nft": max(0, MINIMUM_TOKENS_FOR_NFT - current_tokens)
    })

# MODIFIED NFT MINTING ENDPOINTS

@app.route("/check_nft_eligibility/<user_address>", methods=["GET"])
def check_nft_eligibility(user_address):
    """Check if user is eligible to mint NFT"""
    current_tokens = get_user_tokens(user_address)
    eligible = current_tokens >= MINIMUM_TOKENS_FOR_NFT

    return jsonify({
        "eligible": eligible,
        "current_tokens": current_tokens,
        "required_tokens": MINIMUM_TOKENS_FOR_NFT,
        "tokens_needed": max(0, MINIMUM_TOKENS_FOR_NFT - current_tokens)
    })

@app.route("/mintBadge", methods=["POST"])
def mintBadge():
    """Mint badge if user has enough tokens based on badge type"""
    data = request.get_json()
    badge_type = data.get("badge_type")
    token_uri = data.get("token_uri")
    recipient = data.get("recipient")
    user_address = data.get("user_address")

    if not all([badge_type, token_uri, recipient, user_address]):
        return jsonify({"error": "Missing required fields"}), 400

    # Define cost per badge
    BADGE_COST = {
        "Newbie": 10,
        "Amateur": 30,
        "Intermediate": 50,
        "Pro": 75,
        "entrePROneur": 100
    }

    required_tokens = BADGE_COST.get(badge_type)
    if required_tokens is None:
        return jsonify({"error": f"Invalid badge type: {badge_type}"}), 400

    current_tokens = get_user_tokens(user_address)
    if current_tokens < required_tokens:
        return jsonify({
            "error": f"Insufficient tokens for {badge_type}. You have {current_tokens}, need {required_tokens}",
            "tokens_needed": required_tokens - current_tokens
        }), 400

    try:
        # Deduct the exact number of tokens for this badge type
        if not deduct_tokens(user_address, required_tokens):
            return jsonify({"error": "Token deduction failed"}), 400

        nonce = get_nonce(accountAddress)
        txn = contract.functions.mintBadge(Web3.to_checksum_address(recipient), badge_type, token_uri).build_transaction({
            "from": accountAddress,
            "nonce": nonce,
            "gas": 300000,
            "gasPrice": web3.to_wei("2", "gwei")
        })

        signed_txn = web3.eth.account.sign_transaction(txn, private_key=privateKey)
        tx_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)

        return jsonify({
            "tx_hash": web3.to_hex(tx_hash),
            "tokens_deducted": required_tokens,
            "remaining_tokens": get_user_tokens(user_address),
            "message": f"{badge_type} NFT minted successfully!"
        })
    except Exception as e:
        # Refund if something failed
        add_tokens(user_address, required_tokens)
        return jsonify({"error": str(e)}), 400


@app.route("/uploadMetadata", methods=["POST"])
def upload_metadata():
    """Generates certificate PNG with QR code and pins both PNG and metadata to Pinata in a simplified way."""
    data = request.json
    required_fields = ["student_name", "class_semester", "university", "badge_type", "user_address"]
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

    user_address = data["user_address"]
    student_name = data["student_name"]
    team_name = data["class_semester"]
    university = data["university"]
    badge_name = data["badge_type"]
    now = datetime.now()
    grant_date = now.strftime("%Y-%m-%d")

    # Check tokens
    current_tokens = get_user_tokens(user_address)
    if current_tokens < MINIMUM_TOKENS_FOR_NFT:
        return jsonify({"error": f"Insufficient tokens"}), 400

    if not deduct_tokens(user_address, MINIMUM_TOKENS_FOR_NFT):
        return jsonify({"error": "Failed to deduct tokens"}), 400

    try:
        baseDir = os.path.dirname(os.path.abspath(__file__))
        generated_dir = os.path.join(baseDir, "generated")
        os.makedirs(generated_dir, exist_ok=True)
        output_file = os.path.join(generated_dir, f"generated_{sanitize_filename(student_name)}_{sanitize_filename(badge_name)}.png")

        # Prepare metadata first (with a dummy link)
        metadata = {
            "pinataMetadata": {"name": f"{student_name}-{badge_name}"},
            "pinataContent": {
                "image_cid": "",
                "certificate_url": "",
                "attributes": [
                    {"Student": student_name},
                    {"Class": team_name},
                    {"University": university},
                    {"Date": grant_date},
                    {"Badge Type": badge_name},
                    {"Tokens Used": MINIMUM_TOKENS_FOR_NFT}
                ],
            },
        }

        # Pin metadata first to get its CID
        metadata_cid = uploadMetadataToPinata(metadata)
        metadataURL = f"https://gateway.pinata.cloud/ipfs/{metadata_cid}"

        # Now generate certificate with QR code linking directly to metadata
        generate_certificate(output_file, student_name, team_name, university, metadataURL, badge_name)
        print(f"Checking file path: {output_file}")
        # Pin certificate PNG
        image_cid = test_upload_to_pinata(output_file)
        image_url = f"https://gateway.pinata.cloud/ipfs/{image_cid['cid']}"
        print("CID:", image_cid['cid'])
        print("URL:", f"https://gateway.pinata.cloud/ipfs/{image_url}")

        # Update metadata with PNG link
        metadata = {
            "pinataMetadata": {"name": f"{student_name}-{badge_name}"},
            "pinataContent": {
                "image_cid": image_cid['cid'],
                "certificate_url": image_url,
                "attributes": [
                    {"Student": student_name},
                    {"Class": team_name},
                    {"University": university},
                    {"Date": grant_date},
                    {"Badge Type": badge_name},
                    {"Tokens Used": MINIMUM_TOKENS_FOR_NFT}
                ],
            },
        }

        metadata_cid = uploadMetadataToPinata(metadata)
        metadataURL = f"https://gateway.pinata.cloud/ipfs/{metadata_cid}"

        # Save to local JSON
        record = {
            "student_name": student_name,
            "class_semester": team_name,
            "university": university,
            "badge_type": badge_name,
            "grant_date": grant_date,
            "metadata_uri": metadataURL,
            "user_address": user_address,
            "tokens_used": MINIMUM_TOKENS_FOR_NFT
        }

        if os.path.exists(STUDENT_BADGE_DATA):
            with open(STUDENT_BADGE_DATA, "r") as f:
                badge_data = json.load(f)
        else:
            badge_data = []

        badge_data.append(record)

        with open(STUDENT_BADGE_DATA, "w") as f:
            json.dump(badge_data, f, indent=2)

        return jsonify({"metadata_uri": metadataURL, "certificate_url": image_url})

    except Exception as e:
        add_tokens(user_address, MINIMUM_TOKENS_FOR_NFT)
        return jsonify({"error": str(e)}), 400

# EXISTING ENDPOINTS (unchanged)
@app.route("/canmint/<badge_type>", methods=["GET"])
def canMint(badge_type):
    try:
        result = contract.functions.canMintBadge(badge_type).call()
        minted = contract.functions.getMintedCount(badge_type).call()
        cap = contract.functions.badgeTypes(badge_type).call()[1]
        return jsonify({
            "can_mint": result,
            "minted": minted,
            "cap": cap
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/getMintedCount/<badge_type>", methods=["GET"])
def mintedCount(badge_type):
    try:
        count = contract.functions.getMintedCount(badge_type).call()
        return jsonify({"minted_count": count})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/list_minted_badges", methods=["GET"])
def list_minted_badges():
    metadata_uris = []
    try:
        latest_id = contract.functions.totalSupply().call()
        if latest_id <= 0:
            return jsonify([]), 200
        for token_id in range(1, latest_id + 1):
            metadata_uri = contract.functions.tokenURI(token_id).call()
            metadata_uris.append(metadata_uri)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    results = []
    for metadata_uri in metadata_uris:
        try:
            response = requests.get(metadata_uri)
            if response.status_code != 200:
                continue
            badge_data = response.json()
            certificate_url = badge_data.get('certificate_url', 'N/A')
            attributes = badge_data.get("attributes", [])
            student_collection = {
                list(attr.keys())[0]: list(attr.values())[0] for attr in attributes
            }
            badge_info = OrderedDict([
                ("Student Name", student_collection.get("Student", "N/A")),
                ("Badge Grant Date", student_collection.get("Date", "N/A")),
                ("Badge Type", student_collection.get("Badge Type", "N/A")),
                ("Class or Semester", student_collection.get("Class", "N/A")),
                ("University", student_collection.get("University", "N/A")),
                ("Certificate URL", certificate_url),
                ("Tokens Used", student_collection.get("Tokens Used", "N/A"))
            ])
            results.append(badge_info)
        except Exception as e:
            continue

    return jsonify(results), 200
# Add these endpoints to your existing StudentNFTAPI.py file

@app.route("/admin_add_tokens", methods=["POST"])
def admin_add_tokens():
    """Admin endpoint to add tokens to user balance"""
    data = request.get_json()
    user_address = data.get("user_address")
    token_amount = data.get("token_amount")

    if not user_address or not token_amount:
        return jsonify({"error": "User address and token amount are required"}), 400

    if token_amount <= 0:
        return jsonify({"error": "Token amount must be positive"}), 400

    # Initialize user if not exists
    initialize_user_tokens(user_address, 0)

    # Add tokens
    new_balance = add_tokens(user_address, token_amount)

    return jsonify({
        "user_address": user_address,
        "tokens_added": token_amount,
        "new_balance": new_balance,
        "message": f"Successfully added {token_amount} tokens"
    })

@app.route("/admin_deduct_tokens", methods=["POST"])
def admin_deduct_tokens():
    """Admin endpoint to deduct tokens from user balance"""
    data = request.get_json()
    user_address = data.get("user_address")
    token_amount = data.get("token_amount")

    if not user_address or not token_amount:
        return jsonify({"error": "User address and token amount are required"}), 400

    if token_amount <= 0:
        return jsonify({"error": "Token amount must be positive"}), 400

    # Check if user exists and has sufficient balance
    current_balance = get_user_tokens(user_address)
    if current_balance < token_amount:
        return jsonify({
            "error": f"Insufficient balance. Current: {current_balance}, Requested: {token_amount}"
        }), 400

    # Deduct tokens
    success = deduct_tokens(user_address, token_amount)
    if success:
        new_balance = get_user_tokens(user_address)
        return jsonify({
            "user_address": user_address,
            "tokens_deducted": token_amount,
            "new_balance": new_balance,
            "message": f"Successfully deducted {token_amount} tokens"
        })
    else:
        return jsonify({"error": "Failed to deduct tokens"}), 400

@app.route("/admin_set_tokens", methods=["POST"])
def admin_set_tokens():
    """Admin endpoint to set exact token balance for user"""
    data = request.get_json()
    user_address = data.get("user_address")
    token_amount = data.get("token_amount")

    if not user_address or token_amount is None:
        return jsonify({"error": "User address and token amount are required"}), 400

    if token_amount < 0:
        return jsonify({"error": "Token amount cannot be negative"}), 400

    # Set exact balance
    user_tokens[user_address] = token_amount

    return jsonify({
        "user_address": user_address,
        "new_balance": token_amount,
        "message": f"Successfully set balance to {token_amount} tokens"
    })

@app.route("/admin_get_all_users", methods=["GET"])
def admin_get_all_users():
    """Admin endpoint to get all users and their balances"""
    users_data = []
    for user_address, balance in user_tokens.items():
        users_data.append({
            "user_address": user_address,
            "token_balance": balance
        })

    return jsonify({
        "total_users": len(users_data),
        "users": users_data
    })

@app.route("/admin_badge_eligibility/<user_address>", methods=["GET"])
def admin_badge_eligibility(user_address):
    """Admin endpoint to check badge eligibility for a user"""
    current_tokens = get_user_tokens(user_address)

    # Badge requirements
    badge_requirements = {
        "Newbie": 10,
        "Amateur": 30,
        "Intermediate": 50,
        "Pro": 75,
        "entrePROneur": 100
    }

    eligible_badges = []
    for badge, requirement in badge_requirements.items():
        if current_tokens >= requirement:
            eligible_badges.append({
                "badge": badge,
                "requirement": requirement,
                "eligible": True
            })
        else:
            eligible_badges.append({
                "badge": badge,
                "requirement": requirement,
                "eligible": False,
                "tokens_needed": requirement - current_tokens
            })

    # Determine highest eligible badge
    highest_badge = None
    badge_hierarchy = ["Newbie", "Amateur", "Intermediate", "Pro", "entrePROneur"]
    for badge in reversed(badge_hierarchy):
        if current_tokens >= badge_requirements[badge]:
            highest_badge = badge
            break

    return jsonify({
        "user_address": user_address,
        "current_tokens": current_tokens,
        "badge_eligibility": eligible_badges,
        "highest_eligible_badge": highest_badge
    })

@app.route("/admin_stats", methods=["GET"])
def admin_stats():
    """Admin endpoint to get system statistics"""
    total_users = len(user_tokens)
    total_tokens_distributed = sum(user_tokens.values())
    average_tokens = total_tokens_distributed / total_users if total_users > 0 else 0

    # Badge statistics
    badge_requirements = {
        "Newbie": 10,
        "Amateur": 30,
        "Intermediate": 50,
        "Pro": 75,
        "entrePROneur": 100
    }

    badge_eligible_counts = {}
    for badge, requirement in badge_requirements.items():
        count = sum(1 for balance in user_tokens.values() if balance >= requirement)
        badge_eligible_counts[badge] = count

    return jsonify({
        "total_users": total_users,
        "total_tokens_distributed": total_tokens_distributed,
        "average_tokens_per_user": round(average_tokens, 2),
        "badge_eligible_counts": badge_eligible_counts,
        "active_sessions": len(user_sessions)
    })

@app.route("/health", methods=["GET"])
def health_check():
    """Simple health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "blockchain_connected": web3.is_connected(),
        "total_users": len(user_tokens)
    })

if __name__ == "__main__":
    app.run(debug=True)


@app.route("/admin_batch_fund_and_mint", methods=["POST"])
def admin_batch_fund_and_mint():
    """
    Admin endpoint to read a JSON file of user name -> address,
    mint a Participation NFT to each, and optionally fund with ETH.
    """
    json_file = request.json.get("json_file", r"D:\comp codes\internship_projects\cie\StudentNFT_ver3\IgniteApp\project2\server\data\teamWallets.json")
    badge_type = request.json.get("badge_type", "Participation")
    faucet_enabled = request.json.get("faucet_enabled", False)
    fund_amount_eth = request.json.get("fund_amount_eth", 20)

    try:
        with open(json_file, "r") as f:
            address_map = json.load(f)  # { "Alice": "0x123...", ... }
    except Exception as e:
        return jsonify({"error": f"Failed to load file: {str(e)}"}), 400

    minted = []
    failed = []

    for name, addr in address_map.items():
        try:
            checksum_addr = Web3.to_checksum_address(addr)

            if faucet_enabled:
                # Send 20 ETH from admin account
                tx = {
                    "from": accountAddress,
                    "to": checksum_addr,
                    "value": web3.to_wei(fund_amount_eth, "ether"),
                    "gas": 21000,
                    "gasPrice": web3.to_wei("2", "gwei"),
                    "nonce": get_nonce(accountAddress)
                }
                signed_txn = web3.eth.account.sign_transaction(tx, private_key=privateKey)
                web3.eth.send_raw_transaction(signed_txn.raw_transaction)

            # Mint NFT to user
            token_uri = f"https://example.com/metadata/{name}.json"
            nonce = get_nonce(accountAddress)
            txn = contract.functions.mintBadge(checksum_addr, badge_type, token_uri).build_transaction({
                "from": accountAddress,
                "nonce": nonce,
                "gas": 300000,
                "gasPrice": web3.to_wei("2", "gwei")
            })
            signed_txn = web3.eth.account.sign_transaction(txn, private_key=privateKey)
            tx_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)

            minted.append({
                "name": name,
                "address": addr,
                "tx_hash": web3.to_hex(tx_hash)
            })

        except Exception as e:
            failed.append({
                "name": name,
                "address": addr,
                "error": str(e)
            })

    return jsonify({
        "minted": minted,
        "failed": failed,
        "total_processed": len(address_map),
        "faucet_enabled": faucet_enabled
    })
