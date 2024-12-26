# Twilio IVR System with Flask

A simple Interactive Voice Response (IVR) system built using Flask and Twilio. This system can handle incoming calls, provide menu options, and route calls based on user input.

## Prerequisites

- Python 3.7 or higher
- A Twilio account
- ngrok
- A phone number for testing

## Setup Instructions

### 1. Twilio Account Setup
1. Create a Twilio account at [https://www.twilio.com/try-twilio](https://www.twilio.com/try-twilio)
2. After signing up, note down your:
   - Account SID
   - Auth Token
   - These can be found in your [Twilio Console Dashboard](https://console.twilio.com/)

### 2. Get a Twilio Phone Number
1. In Twilio Console, go to Phone Numbers → Buy a Number
2. Choose a number that supports voice calls
3. For Indian users: Select "India" as country to avoid international charges
4. Purchase the number

### 3. ngrok Setup
1. Download and install ngrok from [https://ngrok.com/download](https://ngrok.com/download)
2. Sign up for a free ngrok account at [https://dashboard.ngrok.com/signup](https://dashboard.ngrok.com/signup)
3. Get your authtoken from [https://dashboard.ngrok.com/get-started/your-authtoken](https://dashboard.ngrok.com/get-started/your-authtoken)
4. Configure ngrok with your authtoken:   ```bash
   ngrok config add-authtoken YOUR_AUTH_TOKEN   ```

### 4. Project Setup
1. Clone this repository:   ```bash
   git clone [repository-url]
   cd [repository-name]   ```

2. Create a virtual environment:   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate   ```

3. Install required packages:   ```bash
   pip install flask twilio python-dotenv   ```

4. Create a `.env` file in the project root:   ```plaintext
   TWILIO_ACCOUNT_SID=your_account_sid_here
   TWILIO_AUTH_TOKEN=your_auth_token_here
   SALES_PHONE_NUMBER=+1234567890
   SUPPORT_PHONE_NUMBER=+1234567890
   PORT=5000   ```

### 5. Running the Application
1. Start the Flask application:   ```bash
   python main.py   ```

2. In a new terminal, start ngrok:   ```bash
   ngrok http 5000   ```

3. Configure Twilio Webhook:
   - Copy the ngrok URL (looks like: https://xxxx-xx-xx-xx-xx.ngrok-free.app)
   - Go to Twilio Console → Phone Numbers → Manage → Active numbers
   - Click on your number
   - Under "Voice & Fax", find "A Call Comes In"
   - Set the webhook URL to your ngrok URL + "/answer"
   - Set method to HTTP POST
   - Save changes

### 6. Verify Your Phone Number (Trial Accounts)
1. Go to Twilio Console → Phone Numbers → Verified Caller IDs
2. Click "+" to add a new number
3. Enter your phone number
4. Complete the verification process

## Testing the IVR

1. Ensure both Flask app and ngrok are running
2. Call your Twilio number from your verified phone number
3. You should hear the welcome message and menu options
4. Test different options:
   - Press 1 for sales
   - Press 2 for support
   - Speak a query

## Important Notes

- Free Twilio accounts have limitations:
  - Trial message played before your actual message
  - Can only call verified numbers
  - Limited credit
- ngrok URL changes every restart (free tier)
- International calling rates apply when using US numbers from other countries

## Troubleshooting

- If calls aren't coming through:
  - Verify Flask app is running
  - Verify ngrok is running
  - Check webhook URL in Twilio console
  - Ensure you're calling from a verified number (trial accounts)
- If you get charged international rates:
  - Consider purchasing a local Twilio number

## License

[Your License Here]
