import streamlit as st
import requests
import json
from datetime import datetime, timedelta
import pandas as pd
from web3 import Web3
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
API_BASE_URL = "http://localhost:5000"  # Your Flask API URL
BLOCKCHAIN_RPC = "http://127.0.0.1:8545"
CONTRACT_ADDRESS = os.getenv("SMART_CONTRACT_ADDRESS")
PRIVATE_KEY = os.getenv("ACCOUNT_PRIVATE_KEY")
ACCOUNT_ADDRESS = os.getenv("ACCOUNT_ADDRESS")

# Badge token requirements
BADGE_TOKEN_REQUIREMENTS = {
    "Newbie": 10,
    "Amateur": 30,
    "Intermediate": 50,
    "Pro": 75,
    "entrePROneur": 100
}

# Token distribution criteria
TOKEN_CRITERIA = {
    "Presence of logo": 5,
    "Adherence of 8 slides limit": 10,
    "Adherence to format": 10,
    "Presence of Tagline": 5,
    "10-12 Points per slides": 10,
    "Ideal font size": 5,
    "Adequate Use of images": 5,
    "Use of relevant statistics": 5,
    "Presence of a BMC": 15,
    "Presence of NABC Canvas": 5,
    "Presence of Value Proposition Canvas": 5
}

# Initialize Web3 connection
@st.cache_data
def load_account_whitelist(json_path="/run/media/purva/Personal Files/CIE_Internship2025/DemoV7/SW2/IgniteApp/project2/server/data/teamWallets.json"):
    try:
        with open(json_path, "r") as f:
            return json.load(f)  # { "Alice": "0x123...", ... }
    except Exception as e:
        st.error(f"Failed to load account whitelist: {e}")
        return {}

@st.cache_resource
def init_web3():
    try:
        web3 = Web3(Web3.HTTPProvider(BLOCKCHAIN_RPC))
        return web3 if web3.is_connected() else None
    except:
        return None

def calculate_signup_bonus(signup_date):
    """Calculate signup bonus based on days since signup"""
    if not signup_date:
        return 0
    
    days_diff = (datetime.now().date() - signup_date).days
    if days_diff <= 1:
        return 20
    elif days_diff <= 2:
        return 10
    elif days_diff <= 3:
        return 5
    else:
        return 0

def send_tokens_to_user(user_address, token_amount):
    """Send tokens to user via API"""
    try:
        # Initialize user if not exists
        response = requests.post(f"{API_BASE_URL}/initialize_user", 
                               json={"user_address": user_address})
        
        # Add tokens to user balance
        # Note: This is a simplified approach. In practice, you might want a dedicated endpoint
        # for admin token allocation
        payload = {
            "user_address": user_address,
            "token_amount": token_amount
        }
        
        # For now, we'll use the existing add_tokens function through a custom endpoint
        # You'll need to add this endpoint to your Flask app
        response = requests.post(f"{API_BASE_URL}/admin_add_tokens", json=payload)
        
        if response.status_code == 200:
            return True, response.json()
        else:
            return False, response.text
    except Exception as e:
        return False, str(e)

def check_user_balance(user_address):
    """Check user's current token balance"""
    try:
        response = requests.get(f"{API_BASE_URL}/get_user_balance/{user_address}")
        if response.status_code == 200:
            return response.json().get("tokens", 0)
        return 0
    except:
        return 0

def determine_eligible_badge(token_balance):
    """Determine the highest badge a user can mint based on token balance"""
    eligible_badges = []
    for badge, requirement in BADGE_TOKEN_REQUIREMENTS.items():
        if token_balance >= requirement:
            eligible_badges.append(badge)
    
    if not eligible_badges:
        return None
    
    # Return the highest tier badge
    badge_hierarchy = ["Newbie", "Amateur", "Intermediate", "Pro", "entrePROneur"]
    for badge in reversed(badge_hierarchy):
        if badge in eligible_badges:
            return badge
    
    return eligible_badges[0]

def mint_badge_for_user(user_address, badge_type, student_name, class_semester, university):
    """Mint badge for user"""
    try:
        # First upload metadata
        metadata_payload = {
            "student_name": student_name,
            "class_semester": class_semester,
            "university": university,
            "badge_type": badge_type,
            "user_address": user_address
        }
        
        metadata_response = requests.post(f"{API_BASE_URL}/uploadMetadata", 
                                        json=metadata_payload)
        
        if metadata_response.status_code != 200:
            return False, f"Metadata upload failed: {metadata_response.text}"
        
        metadata_uri = metadata_response.json().get("metadata_uri")
        # Then mint the badge
        mint_payload = {
            "badge_type": badge_type,
            "token_uri": metadata_uri,
            "recipient": user_address,
            "user_address": user_address
        }
        
        mint_response = requests.post(f"{API_BASE_URL}/mintBadge", json=mint_payload)
        
        if mint_response.status_code == 200:
            result = mint_response.json()
            result["metadata_uri"] = metadata_uri 
            return True, result
        else:
            return False, mint_response.text
            
    except Exception as e:
        return False, str(e)

# Streamlit App
def main():
    st.set_page_config(page_title="Admin Dashboard", page_icon="🏆", layout="wide")
    st.title("🏆 Student NFT Badge Admin Dashboard")
    st.markdown("---")

    # Load allowed users
    account_whitelist = load_account_whitelist()
    if not account_whitelist:
        st.error("No approved addresses found. Please check accounts.json.")
        return

    # Selection dropdown
    selected_name = st.selectbox("Select Approved User", list(account_whitelist.keys()))
    selected_address = account_whitelist[selected_name]

    st.success(f"Selected: {selected_name} ({selected_address})")

    # Sidebar for navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox("Choose a page",
        ["Token Evaluation", "Badge Management", "User Overview", "System Status"])

    if page == "Token Evaluation":
        token_evaluation_page(selected_name, selected_address)
    elif page == "Badge Management":
        badge_management_page(selected_name, selected_address)
    elif page == "User Overview":
        user_overview_page(selected_name, selected_address)
    elif page == "System Status":
        system_status_page()


def token_evaluation_page(user_name, user_address):
    st.header("📊 Token Evaluation & Distribution")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Project Evaluation Form")
        
        # Team Information
        # st.markdown("### Team Information")
        # team_name = st.text_input("Team Name")
        # student_name = st.text_input("Student Name")
        # class_semester = st.text_input("Class/Semester")
        # university = st.text_input("University")
        # user_address = st.text_input("Wallet Address", placeholder="0x...")
        
        # Signup date for bonus calculation
        signup_date = st.date_input("Signup Date", value=datetime.now().date())
        
        st.markdown("### Evaluation Criteria")
        
        # Create evaluation form
        evaluation_scores = {}
        total_possible = sum(TOKEN_CRITERIA.values()) + 20  # +20 for max signup bonus
        
        # Signup bonus calculation
        signup_bonus = calculate_signup_bonus(signup_date)
        st.info(f"Signup Bonus: {signup_bonus} tokens (signed up {(datetime.now().date() - signup_date).days} days ago)")
        
        # Evaluation criteria checkboxes
        for criteria, points in TOKEN_CRITERIA.items():
            evaluation_scores[criteria] = st.checkbox(
                f"{criteria} (+{points} tokens)", 
                key=criteria
            )
        
        # Calculate total tokens
        earned_tokens = signup_bonus
        for criteria, awarded in evaluation_scores.items():
            if awarded:
                earned_tokens += TOKEN_CRITERIA[criteria]
        
    with col2:
        st.subheader("Evaluation Summary")

        # Display breakdown
        st.markdown("### Token Breakdown")
        st.write(f"**Signup Bonus:** {signup_bonus} tokens")

        for criteria, awarded in evaluation_scores.items():
            if awarded:
                st.write(f"✅ {criteria}: +{TOKEN_CRITERIA[criteria]} tokens")

        st.markdown("---")
        st.metric("Total Tokens", earned_tokens, f"out of {total_possible}")

        # Progress bar
        progress = min(earned_tokens / total_possible, 1.0)
        st.progress(progress)

        # Award tokens button
        if st.button("🎁 Award Tokens", type="primary", disabled=not all([user_name, user_address])):
            if earned_tokens > 0:
                with st.spinner("Awarding tokens..."):
                    success, result = send_tokens_to_user(user_address, earned_tokens)

                if success:
                    st.success(f"Successfully awarded {earned_tokens} tokens to {user_address}")

                    # Check if user can mint a badge
                    current_balance = check_user_balance(user_address)
                    eligible_badge = determine_eligible_badge(current_balance)

                    if eligible_badge:
                        st.info(f"🏆 User is now eligible for {eligible_badge} badge! (Balance: {current_balance} tokens)")
                else:
                    st.error(f"Failed to award tokens: {result}")
            else:
                st.warning("No tokens to award based on current evaluation.")

def badge_management_page(user_name, user_address):
    st.header("🏆 Badge Management")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Manual Badge Minting")
        
        # User information for badge minting
        #mint_user_address = st.text_input("User Wallet Address", key="mint_address")
        mint_student_name = st.text_input("Student Name", key="mint_student")
        mint_class = st.text_input("Team Name", key="mint_class")
        mint_university = st.text_input("Branch", key="mint_university")
        
        # Badge type selection
        selected_badge = st.selectbox("Badge Type", list(BADGE_TOKEN_REQUIREMENTS.keys()))
        required_tokens = BADGE_TOKEN_REQUIREMENTS[selected_badge]
        
        if user_address:
            current_balance = check_user_balance(user_address)
            st.info(f"Current Balance: {current_balance} tokens")
            st.info(f"Required for {selected_badge}: {required_tokens} tokens")
            
            can_mint = current_balance >= required_tokens
            
            if st.button("🎖️ Mint Badge", 
                        disabled=not can_mint or not all([user_address, mint_student_name, mint_class, mint_university]),
                        type="primary"):
                
                with st.spinner(f"Minting {selected_badge} badge..."):
                    success, result = mint_badge_for_user(
                        user_address, selected_badge, mint_student_name,
                        mint_class, mint_university
                    )
                
                if success:
                    metadata_uri = result.get("metadata_uri")

                    st.balloons()
                    st.success(f"🎉 Successfully minted **{selected_badge}** badge for **{mint_student_name}**!")

                    if metadata_uri:
                        try:
                            # Fetch metadata JSON from IPFS
                            metadata_response = requests.get(metadata_uri)
                            if metadata_response.status_code == 200:
                                metadata = metadata_response.json()
                                cert_url = metadata.get("pinataContent", {}).get("certificate_url")

                                # If not found, assume top-level
                                if not cert_url:
                                    cert_url = metadata.get("certificate_url")

                                if cert_url:
                                    st.image(cert_url, caption="🏆 NFT Certificate", use_container_width=True)
                                else:
                                    st.warning("Certificate image not found in metadata.")
                            else:
                                st.warning("Failed to fetch metadata from IPFS.")
                        except Exception as e:
                            st.error(f"Error loading certificate: {e}")
                    else:
                        st.warning("No metadata URI returned.")
                else:
                    st.error(f"Failed to mint badge: {result}")
    
    with col2:
        st.subheader("Badge Requirements")

        # Display badge hierarchy
        for badge, requirement in BADGE_TOKEN_REQUIREMENTS.items():
            st.write(f"**{badge}:** {requirement} tokens")

        st.markdown("---")
        st.subheader("Auto Badge Suggestion")

        # Input wallet address and sync to session_state
        check_address = st.text_input("Check Address for Auto-Badge", key="check_auto")

        if check_address:
            check_address = check_address.strip()
            # Sync this address so the "Manual Badge Minting" can use it
            st.session_state["selected_user_address"] = check_address

            if st.button("Check Eligibility"):
                balance = check_user_balance(check_address)
                eligible_badge = determine_eligible_badge(balance)

                if eligible_badge:
                    st.success(f"✅ Eligible for: **{eligible_badge}** badge")
                    st.info(f"Current balance: {balance} tokens")
                else:
                    st.warning("❌ Not eligible for any badge yet")
                    min_requirement = min(BADGE_TOKEN_REQUIREMENTS.values())
                    st.info(f"Need at least {min_requirement} tokens for Newbie badge")

def user_overview_page(user_name, user_address):
    st.header("👥 User Overview")
    
    # User lookup
    lookup_address = st.text_input("Enter user address to lookup:")
    
    if lookup_address:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("User Balance")
            balance = check_user_balance(lookup_address)
            st.metric("Current Tokens", balance)
            
            # Show eligibility for each badge
            st.subheader("Badge Eligibility")
            for badge, requirement in BADGE_TOKEN_REQUIREMENTS.items():
                eligible = balance >= requirement
                status = "✅" if eligible else "❌"
                st.write(f"{status} {badge}: {requirement} tokens")
        
        with col2:
            st.subheader("Quick Actions")
            
            # Add tokens manually
            add_tokens = st.number_input("Add Tokens", min_value=0, step=1)
            if st.button("Add Tokens") and add_tokens > 0:
                success, result = send_tokens_to_user(lookup_address, add_tokens)
                if success:
                    st.success(f"Added {add_tokens} tokens")
                else:
                    st.error(f"Failed: {result}")
    
    # Display all minted badges
    st.markdown("---")
    st.subheader("🏆 All Minted Badges")
    
    if st.button("Refresh Badge List"):
        try:
            response = requests.get(f"{API_BASE_URL}/list_minted_badges")
            if response.status_code == 200:
                badges = response.json()
                if badges:
                    df = pd.DataFrame(badges)
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info("No badges minted yet.")
            else:
                st.error("Failed to fetch badge list")
        except Exception as e:
            st.error(f"Error: {str(e)}")

def system_status_page():
    st.header("⚙️ System Status")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("API Status")
        
        # Check API health
        try:
            response = requests.get(f"{API_BASE_URL}/get_user_balance/0x0000000000000000000000000000000000000000")
            api_status = "🟢 Online" if response.status_code in [200, 400] else "🔴 Offline"
        except:
            api_status = "🔴 Offline"
        
        st.write(f"Flask API: {api_status}")
        
        # Check blockchain connection
        web3 = init_web3()
        blockchain_status = "🟢 Connected" if web3 and web3.is_connected() else "🔴 Disconnected"
        st.write(f"Blockchain: {blockchain_status}")
        
        if web3 and web3.is_connected():
            try:
                latest_block = web3.eth.block_number
                st.write(f"Latest Block: {latest_block}")
            except:
                st.write("Block info unavailable")
    
    with col2:
        st.subheader("Configuration")
        
        st.write("**Badge Token Requirements:**")
        for badge, tokens in BADGE_TOKEN_REQUIREMENTS.items():
            st.write(f"- {badge}: {tokens} tokens")
        
        st.write("**API Endpoint:**")
        st.code(API_BASE_URL)
        
        st.write("**Contract Address:**")
        st.code(CONTRACT_ADDRESS or "Not configured")

if __name__ == "__main__":
    main()
