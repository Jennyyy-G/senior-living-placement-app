# senior-living-placement-app
Senior Living Placement Assistant is an AI-powered application that helps match seniors with appropriate living communities based on audio intake interviews.
#

Features

🎧 Audio Transcription: Automatically transcribes client intake interviews using OpenAI Whisper

🤖 AI Preference Extraction: Uses GPT-4 to extract structured preferences from conversations

🔍 Smart Filtering: Filters communities based on care level, budget, waitlist, and amenities

📍 Geographic Ranking: Ranks by distance from preferred locations

💰 Priority System: Prioritizes revenue-generating partners

📊 Interactive Dashboard: Easy-to-use Streamlit interface

#

Enter your OpenAI API key in the sidebar when the app opens

Configure Secrets (Optional)

Upload Files: Upload the ZIP file containing audio and the Excel file with community data

Transcribe: Click to transcribe the audio and extract preferences

Process: Filter and rank communities based on extracted preferences

Review: View top 5 recommendations with detailed explanations

Download: Export results as CSV
#

# Data Requirements

Audio File - Must be in ZIP format containing .m4a file

Community Excel File - Required columns:

CommunityID

Type of Service

Enhanced

Enriched

Est. Waitlist Length

Monthly Fee

Contract (w rate)?

Work with Placement?

ZIP or Postal Code

Geocode (optional)

Apartment Type

Security Notes

#

# Troubleshooting

API Key Issues: Make sure your OpenAI API key has sufficient credits and access to Whisper and GPT-4 models.

File Upload Errors: Ensure files are in the correct format (.zip for audio, .xlsx for data).

Geocoding Errors: The app uses free geocoding services which may have rate limits. If you see errors, wait a moment and try again.

Distance Calculation Issues: Some communities may not have valid coordinates. These will be ranked lower.

#

# License

[Your License Here]

#

# Contributors

Team 2
