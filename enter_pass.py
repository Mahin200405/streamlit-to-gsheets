import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime

# Google Sheets Authentication
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["connections"]["gsheets"], scope)
client = gspread.authorize(creds)

# Open the Google Sheet
spreadsheet = client.open_by_key(st.secrets["connections"]["gsheets"]["spreadsheet"])
worksheet = spreadsheet.worksheet("Example 1")

def load_data():
    """Fetch data from Google Sheets and return as a pandas DataFrame"""
    data = worksheet.get_all_records()
    return pd.DataFrame(data)

df = load_data()

password = "BITS GOA"

# Initialize session state for teams
if "teams" not in st.session_state:
    st.session_state["teams"] = df.set_index("Teamname").to_dict(orient="index")

def sync_with_gsheets(teamname):
    """Update only the specific team's row without overwriting other teams"""
    df = load_data()  # Reload latest data

    if teamname in df["Teamname"].values:
        index = df[df["Teamname"] == teamname].index[0]
        df.at[index, "No of tries"] = st.session_state["teams"][teamname]["No of tries"]
        df.at[index, "Answered correctly?"] = st.session_state["teams"][teamname]["Answered correctly?"]
        df.at[index, "Time"] = st.session_state["teams"][teamname]["Time"]
    else:
        new_row = pd.DataFrame([{
            "Teamname": teamname, 
            "No of tries": st.session_state["teams"][teamname]["No of tries"], 
            "Answered correctly?": st.session_state["teams"][teamname]["Answered correctly?"], 
            "Time": st.session_state["teams"][teamname]["Time"]
        }])
        df = pd.concat([df, new_row], ignore_index=True)

    worksheet.clear()  # Clear the sheet before updating
    worksheet.update([df.columns.values.tolist()] + df.values.tolist())  # Update the Google Sheet

def give_tries():
    """Manage the password attempts for a given team"""
    teamname = st.session_state.get("teamname")

    if not teamname:
        return  # No team selected

    if teamname not in st.session_state["teams"]:
        st.error("Unexpected Error: Team not found in local database.")
        return

    team_data = st.session_state["teams"][teamname]

    # Initialize session state tries if first time
    if "tries" not in st.session_state:
        st.session_state["tries"] = team_data["No of tries"]

    # Display team status
    st.subheader(f"Team: {teamname}")
    st.write(f"Remaining Attempts: {st.session_state['tries']}")

    if st.session_state["tries"] > 0 and team_data["Answered correctly?"] != "Yes":
        with st.form("Password Form"):
            entered_password = st.text_input("Enter your answer:", type="password")
            submit = st.form_submit_button("Submit")

            if submit:
                if entered_password == password:
                    st.success("✅ CORRECT")
                    st.session_state["teams"][teamname]["Answered correctly?"] = "Yes"
                    st.session_state["teams"][teamname]["Time"] = datetime.now().strftime("%H:%M:%S")  

                    sync_with_gsheets(teamname)  
                    st.write(f"🎉 Congratulations! You have answered correctly at **{st.session_state['teams'][teamname]['Time']}**.")
                else:
                    st.session_state["tries"] -= 1
                    st.session_state["teams"][teamname]["No of tries"] = st.session_state["tries"]

                    
                    if st.session_state["tries"] == 0:
                        st.session_state["teams"][teamname]["Answered correctly?"] = "No"

                    sync_with_gsheets(teamname)  

                    if st.session_state["tries"] > 0:
                        st.error(f"❌ Incorrect! You have {st.session_state['tries']} attempts left.")
                    else:
                        st.error("❌ You have run out of attempts! Answer marked as 'No'.")
    
    elif team_data["Answered correctly?"] == "Yes":
        st.success(f"✅ You have already answered correctly at **{team_data.get('Time', 'Unknown Time')}**.")
    else:
        st.error("❌ No more attempts left!")

def write_new(teamname):
    """Check if the team exists, and only add if necessary"""
    df = load_data()

    if teamname in df["Teamname"].values:
        team_data = df[df["Teamname"] == teamname].iloc[0].to_dict()
        st.session_state["teams"][teamname] = {
            "No of tries": team_data["No of tries"],
            "Answered correctly?": team_data["Answered correctly?"],
            "Time": team_data.get("Time", "")
        }
        st.session_state["teamname"] = teamname
        st.session_state["tries"] = st.session_state["teams"][teamname]["No of tries"]
        st.info(f"🔄 Loaded existing team '{teamname}' with {st.session_state['tries']} attempts left.")
        give_tries()
    else:
        st.session_state["teams"][teamname] = {"No of tries": 3, "Answered correctly?": "", "Time": ""}
        sync_with_gsheets(teamname)  
        st.success(f"✅ Team '{teamname}' registered successfully!")
        st.session_state["teamname"] = teamname
        st.session_state["tries"] = 3
        give_tries()

st.title("Competition Page")

if "teamname" not in st.session_state:
    teamname = st.text_input("Enter your team name:")
    if st.button("Next"):
        if not teamname.strip():
            st.error("ERROR: Please enter a valid team name.")
        else:
            write_new(teamname)
else:
    give_tries()
