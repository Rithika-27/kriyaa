from flask import Flask, render_template, request, redirect, url_for, flash, session, make_response,jsonify
from pymongo import MongoClient
from reportlab.pdfgen import canvas  # Using ReportLab for PDF generation
from reportlab.lib.pagesizes import letter
import os  # For managing file paths
from PyPDF2 import PdfReader, PdfWriter
from xhtml2pdf import pisa
from io import BytesIO
import PyPDF2  

app = Flask(__name__)
app.secret_key = 'xyz1234nbg789ty8inmcv2134'  # Make sure this key is kept secure

# MongoDB connection
MONGO_URI = "mongodb+srv://Entries:ewp2025@cluster0.1tuj7.mongodb.net/event-kriya?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI)
db = client["event-kriya"]
event_collection = db["event-entries"]

# Main route for home
@app.route('/')
def home():
    # session.clear()  # Clear all session data for a new event
    return render_template('home.html')

@app.route('/event-instructions', methods=['GET', 'POST'])
def event_instructions():
    if request.method == 'POST':
        return redirect(url_for('event_detail'))
    return render_template('event_instruction.html')

# Event Details Form
@app.route('/event-detail', methods=['GET', 'POST'])
def event_detail():
    if request.method == 'POST':
        # Collect event details and store in session
        event_details = {
            'secretary_name': request.form['secretary_name'],
            'secretary_roll_number': request.form['secretary_roll_number'],
            'secretary_mobile': request.form['secretary_mobile'],
            'convenor_name': request.form['convenor_name'],
            'convenor_roll_number': request.form['convenor_roll_number'],
            'convenor_mobile': request.form['convenor_mobile'],
            'faculty_advisor_name': request.form['faculty_advisor_name'],
            'faculty_advisor_designation': request.form['faculty_advisor_designation'],
            'faculty_advisor_contact': request.form['faculty_advisor_contact'],
            'judge_name': request.form['judge_name'],
            'judge_designation': request.form['judge_designation'],
            'judge_contact': request.form['judge_contact']
        }
        session['event_details'] = event_details
        return redirect(url_for('event_page'))
    return render_template('event_detail.html')

# Event Data Form
@app.route('/event', methods=['GET', 'POST'])
def event_page():
    if request.method == 'POST':
        # Collect event data and store in session
        event_data = {
            'day_1': 'day_1' in request.form,
            'day_2': 'day_2' in request.form,
            'day_3': 'day_3' in request.form,
            'two_days': request.form.get('two_days'),
            'rounds': request.form.get('rounds'),
            'participants': request.form.get('participants'),
            'individual': 'individual' in request.form,
            'team': 'team' in request.form,
            'team_min': request.form.get('team_min'),
            'team_max': request.form.get('team_max'),
            'halls_required': request.form.get('halls_required'),
            'preferred_halls': request.form.get('preferred_halls'),
            'slot': request.form.get('slot'),
            'extension_boxes': request.form.get('extension_boxes'),
            'event_description': request.form.get('event_description'),
            'event_location': request.form.get('event_location')
        }
        session['event_data'] = event_data
        return redirect(url_for('items_page'))
    return render_template('event.html')


@app.route('/items', methods=['GET', 'POST'])
def items_page():
    if 'event_items' not in session:
        session['event_items'] = []

    if request.method == 'POST':
        # Collect item data from the form and store it in the session
        try:
            item_data = {
                "sno": request.form.get("sno"),
                "item_name": request.form.get("item_name"),
                "quantity": int(request.form.get("quantity")),
                "price_per_unit": float(request.form.get("price_per_unit")),
                "total_price": int(request.form.get("quantity")) * float(request.form.get("price_per_unit"))
            }

            # Validate required fields
            if not item_data["item_name"] or not item_data["quantity"]:
                flash("Item name and quantity are required.")
                return redirect(url_for('items_page'))

            # Append item to session
            session['event_items'].append(item_data)
            flash("Item added successfully!")
            return redirect(url_for('event_summary'))
        except ValueError:
            flash("Please enter valid numeric values for quantity and price.")
            return redirect(url_for('items_page'))

    return render_template('items.html', event_items=session['event_items'])

# Event Summary Form
@app.route('/event-summary', methods=['GET', 'POST'])
def event_summary():
    if request.method == 'POST':
        event_name = request.form.get('name')
        tagline = request.form.get('tagline')
        about = request.form.get('about')
        rounds = []

        round_count = int(request.form.get('round_count', 0))
        for i in range(round_count):
            rounds.append({
                "round_no": i + 1,
                "name": request.form.get(f'round_name_{i}'),
                "description": request.form.get(f'round_description_{i}'),
                "rules": request.form.get(f'round_rules_{i}')
            })

        session['event_summary'] = {
            "name": event_name,
            "tagline": tagline,
            "about": about,
            "rounds": rounds
        }
        return redirect(url_for('preview'))
    return render_template('event_form.html')


@app.route('/preview', methods=['GET'])
def preview():
    try:
        # Retrieve event details, event data, event items, and event form data from session
        event_details = session.get('event_details', {})
        event_data = session.get('event_data', {})
        event_items = session.get('event_items', [])
        event_form_data = session.get('event_form_data', {})

        # Pass all the data to the template
        return render_template('preview.html', 
                               event_details=event_details, 
                               event_data=event_data,
                               event_items=event_items,
                               event_form_data=event_form_data)
    except Exception:
        return jsonify({"status": "error", "message": "Error retrieving preview data"}), 500
@app.route('/submit_event', methods=['POST'])
def submit_event():
    try:
        # Get the request JSON data
        all_event_data = request.get_json()  # Correct method to get JSON data
        event_details = all_event_data.get('eventDetails')
        event_data = all_event_data.get('eventData')
        event_items = all_event_data.get('eventItems')  # Correct field name should match
        event_summary = all_event_data.get('eventFormData')

        # Log the received data to ensure it's correct
        print("Received event details:", event_details)
        print("Received event data:", event_data)
        print("Received event items:", event_items)  # Log items
        print("Received event summary:", event_summary)

        # Generate a new event ID based on the last event ID in the database
        existing_event = event_collection.find_one(sort=[("event_id", -1)])
        if existing_event and "event_id" in existing_event:
            last_event_num = int(existing_event["event_id"][4:])
            new_event_id = f"EVNT{last_event_num + 1:02d}"
        else:
            new_event_id = "EVNT01"

        # Prepare the event entry for the database
        event_entry = {
            "event_id": new_event_id,
            "details": event_details,
            "event": event_data,
            "items": event_items,
            "form": event_summary,
        }
        print("Event Entry to be inserted:", event_entry)
        
        # Insert data into the database
        event_collection.insert_one(event_entry)

        session["event_id"] = new_event_id

        return jsonify({"status": "success", "message": "Event submitted successfully!", "event_id": new_event_id}), 200

    except Exception as e:
        print("Error during event submission:", str(e))
        return jsonify({"status": "error", "message": str(e)}), 500


# Confirmation Page
@app.route('/confirm')
def confirm_page():
    return render_template('confirm.html')

@app.route('/view-preview', methods=['GET'])
def view_preview():
    event_id = session.get("event_id")  # Retrieve event_id from session
    if not event_id:
        flash("No event ID found in session.")
        return redirect(url_for('event_page'))

    event_data = event_collection.find_one({"event_id": event_id})
    if not event_data:
        flash("Event data not found.")
        return redirect(url_for('event_page'))

    try:
        # Render the first page
        form_data = event_data.get("details", {})
        html_content_page_1 = render_template(
            'event_preview.html',
            event_id=event_id,
            form_data=form_data,
            event_data=event_data
        )
        pdf_output_page_1 = generate_pdf(html_content_page_1)

        # Render the second page
        event_details = event_data.get("form", {})
        html_content_page_2 = render_template(
            'event_preview_second_page.html',
            event_id=event_id,
            event_details=event_details,
            event_data=event_data
        )
        pdf_output_page_2 = generate_pdf(html_content_page_2)

        # Render the third page (items preview)
        items = event_data.get("items", [])
        html_content_page_3 = render_template(
            'items_preview.html',
            event_id=event_id,
            items=items,
            event_data=event_data
        )
        pdf_output_page_3 = generate_pdf(html_content_page_3)

        # Combine PDFs
        combined_pdf_output = combine_pdfs(
            pdf_output_page_1,
            pdf_output_page_2,
            pdf_output_page_3
        )

        # Return combined PDF
        response = make_response(combined_pdf_output.read())
        response.headers["Content-Type"] = "application/pdf"
        response.headers["Content-Disposition"] = f"attachment; filename=event_{event_id}_preview_combined.pdf"
        return response

    except Exception as e:
        print(f"Error during preview: {e}")
        flash("An error occurred while generating the preview.")
        return redirect(url_for('event_page'))


def generate_pdf(html_content):
    """Generate a PDF from HTML content."""
    pdf_output = BytesIO()
    pisa_status = pisa.CreatePDF(html_content, dest=pdf_output)
    if pisa_status.err:
        raise ValueError("Error generating PDF.")
    pdf_output.seek(0)
    return pdf_output


def combine_pdfs(*pdf_outputs):
    """Combine multiple PDF outputs into a single PDF."""
    pdf_merger = PyPDF2.PdfMerger()
    for pdf_output in pdf_outputs:
        pdf_output.seek(0)
        pdf_merger.append(pdf_output)
    combined_pdf_output = BytesIO()
    pdf_merger.write(combined_pdf_output)
    combined_pdf_output.seek(0)
    return combined_pdf_output


# Assume `event_collection` is a valid MongoDB collection instance

if __name__ == '__main__':
    app.run(debug=True)
