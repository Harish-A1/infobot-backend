# FastAPI Chatbot Backend

This is the backend service for the Flutter chatbot application, providing persistent message history using Supabase.

## Setup Instructions

1. **Supabase Setup**:
   - Create a free project on [Supabase](https://supabase.com).
   - Go to the SQL Editor in your Supabase dashboard.
   - Copy the contents of `schema.sql` and run it to create the required tables and views.

2. **Environment Variables**:
   - Copy the `.env.example` file to `.env`:
     ```bash
     copy .env.example .env
     ```
   - Edit `.env` and insert your Supabase Project URL and anon/public API Key.

3. **Install Dependencies**:
   - Create a virtual environment (optional but recommended) and install the packages:
     ```bash
     python -m venv venv
     venv\Scripts\activate
     pip install -r requirements.txt
     ```

4. **Run the Server**:
   - Start the FastAPI server using uvicorn:
     ```bash
     uvicorn main:app --reload
     ```
   - The server will run at `http://localhost:8000`.
