from flask import Flask, flash, redirect, url_for, render_template, request, session, send_file, jsonify
from pymongo import MongoClient
from io import BytesIO
from xhtml2pdf import pisa
from bson import ObjectId

app = Flask(__name__)
app.secret_key = 'xyz1234nbg789ty8inmcv2134'

# MongoDB connection
MONGO_URI = "mongodb+srv://Entries:ewp2025@cluster0.1tuj7.mongodb.net/event-kriya?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI)
db = client["event-kriya"]
event_collection = db["event-entries"]

@app.route('/')
def home():
    session.pop("event_id", None)  # Clear session for a new event
    return render_template('home.html')

@app.route('/event-instructions', methods=['GET', 'POST'])
def event_instructions():
    if request.method == 'POST':
        return redirect(url_for('event_detail'))
    return render_template('event_instruction.html')

@app.route('/event-detail', methods=['GET', 'POST'])
def event_detail():
    if request.method == 'POST':
        form_data = {
            "secretary": {
                "name": request.form.get("secretary_name"),
                "roll_number": request.form.get("secretary_roll_number"),
                "mobile": request.form.get("secretary_mobile"),
            },
            "convenor": {
                "name": request.form.get("convenor_name"),
                "roll_number": request.form.get("convenor_roll_number"),
                "mobile": request.form.get("convenor_mobile"),
            },
            "faculty_advisor": {
                "name": request.form.get("faculty_advisor_name"),
                "designation": request.form.get("faculty_advisor_designation"),
                "contact": request.form.get("faculty_advisor_contact"),
            },
            "judge": {
                "name": request.form.get("judge_name"),
                "designation": request.form.get("judge_designation"),
                "contact": request.form.get("judge_contact"),
            }
        }

        try:
            event_id = session.get("event_id")
            if not event_id:
                last_event = event_collection.find_one(sort=[("event_id", -1)])
                if last_event and "event_id" in last_event:
                    last_event_num = int(last_event["event_id"][4:])
                    event_id = f"EVNT{last_event_num + 1:02d}"
                else:
                    event_id = "EVNT01"
                session["event_id"] = event_id

            event_collection.update_one(
                {"event_id": event_id},
                {
                    "$set": {"event_id": event_id, "status": "temporary"},
                    "$push": {
                        "event_details.secretary": form_data["secretary"],
                        "event_details.convenor": form_data["convenor"],
                        "event_details.faculty_advisor": form_data["faculty_advisor"],
                        "event_details.judge": form_data["judge"]
                    }
                },
                upsert=True
            )
            flash("Event details saved temporarily!")
            return redirect(url_for('event_page'))
        except Exception as e:
            print(f"Error saving event details: {e}")
            flash("An error occurred while saving event details.")
            return redirect(url_for('event_detail'))

    return render_template('event_detail.html')

@app.route('/event', methods=['GET', 'POST'])
def event_page():
    event_id = session.get("event_id")
    if not event_id:
        flash("Event ID not found in session.")
        return redirect(url_for('home'))

    if request.method == 'POST':
        event_data = {
            "day_1": bool(request.form.get("day_1")),
            "day_2": bool(request.form.get("day_2")),
            "day_3": bool(request.form.get("day_3")),
            "participants": request.form.get("participants", "").strip(),
            "halls_required": request.form.get("halls_required", "").strip(),
            "team_min": request.form.get("team_min", "").strip(),
            "team_max": request.form.get("team_max", "").strip(),
        }

        if not event_data["participants"] or not event_data["halls_required"]:
            flash("Please fill in all the required fields.")
            return redirect(url_for('event_page'))

        try:
            event_collection.update_one(
                {"event_id": event_id},
                {"$set": {"event": event_data}}
            )
            flash("Event details updated successfully!")
            return redirect(url_for('items_page'))
        except Exception as e:
            print(f"Error saving event data to MongoDB: {e}")
            flash("An error occurred while updating event details.")
            return redirect(url_for('event_page'))

    return render_template('event.html')

@app.route('/items', methods=['GET', 'POST'])
def items_page():
    event_id = session.get("event_id")
    if not event_id:
        flash("Event ID not found.")
        return redirect(url_for('home'))

    if request.method == 'POST':
        items_data = {
            "sno": request.form.get("sno"),
            "item_name": request.form.get("item_name"),
            "quantity": request.form.get("quantity"),
            "price_per_unit": request.form.get("price_per_unit"),
            "total_price": request.form.get("total_price"),
        }

        if not items_data["item_name"] or not items_data["quantity"]:
            flash("Item name and quantity are required.")
            return redirect(url_for('items_page'))

        try:
            event_collection.update_one(
                {"event_id": event_id},
                {"$push": {"items": items_data}}
            )
            flash("Item details saved successfully!")
            return redirect(url_for('event_summary'))
        except Exception as e:
            print(f"Error saving item data to MongoDB: {e}")
            flash("An error occurred while saving item details.")
            return redirect(url_for('items_page'))

    return render_template('items.html')

@app.route('/event-summary', methods=['GET', 'POST'])
def event_summary():
    if request.method == 'POST':
        event_name = request.form.get('name')
        tagline = request.form.get('tagline')
        about = request.form.get('about')
        rounds = []

        round_count = int(request.form.get('round_count', 0))
        for i in range(round_count):
            round_name = request.form.get(f'round_name_{i}')
            round_description = request.form.get(f'round_description_{i}')
            round_rules = request.form.get(f'round_rules_{i}')
            rounds.append({
                "round_no": i + 1,
                "name": round_name,
                "description": round_description,
                "rules": round_rules
            })

        try:
            event_collection.update_one(
                {"event_id": session.get("event_id")},
                {"$set": {
                    "name": event_name,
                    "tagline": tagline,
                    "about": about,
                    "rounds": rounds
                }},
                upsert=True
            )
            flash("Event summary saved successfully!")
        except Exception as e:
            print(f"Error saving event summary: {e}")
            flash("An error occurred while saving the event summary.")

        return redirect(url_for('confirm_submission'))

    return render_template('event_form.html')

@app.route('/confirm', methods=['GET', 'POST'])
def confirm_submission():
    event_id_str = session.get("event_id")

    if not event_id_str:
        flash("Error: Event ID not found in session.")
        return redirect(url_for('event_detail'))

    try:
        event = event_collection.find_one({"event_id": event_id_str})

        if not event:
            flash("Error: Event not found.")
            return redirect(url_for('event_detail'))

        event_id_from_db = event.get("event_id")

        if not event_id_from_db:
            flash("Error: Event ID not found in the event document.")
            return redirect(url_for('event_detail'))

        flash(f"Event {event_id_from_db} retrieved successfully!")
        return render_template('confirm.html', event_id=event_id_from_db)

    except Exception as e:
        print(f"Error retrieving event: {e}")
        flash("An error occurred during event retrieval. Please try again.")
        return redirect(url_for('event_page'))

def get_event_details(event_id):
    event = event_collection.find_one({"event_id": event_id})
    if event:
        event.pop("_id", None)
    return event

@app.route('/event_preview/<event_id>', methods=['GET'])
def event_preview(event_id):
    event_details = get_event_details(event_id)
    items = event_details.get('event_details', {}).get('items', [])
    return render_template('preview.html', details=event_details, items=items)

@app.route('/final_submit', methods=['POST'])
def final_submit():
    event_id = request.form.get('event_id')
    event_details = get_event_details(event_id)

    html = render_template('pdf_template.html', details=event_details)
    pdf_stream = BytesIO()
    pisa_status = pisa.CreatePDF(html, dest=pdf_stream)

    if pisa_status.err:
        return "Error generating PDF", 500

    pdf_stream.seek(0)
    return send_file(pdf_stream, as_attachment=True, download_name=f'event_{event_id}_details.pdf', mimetype='application/pdf')

if __name__ == '__main__':
    app.run(debug=True)
