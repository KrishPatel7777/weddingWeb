from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from functools import wraps
import os

app = Flask(__name__)
# Generate a random secret key for sessions
app.secret_key = 'parampara-wedding-planner-2026-secret-key-change-this'

# MongoDB Atlas Connection
MONGO_URI = os.environ.get("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client['parampara_db']
contacts_collection = db['contacts']
admins_collection = db['admins']

# Create admin user if not exists (Run this once)
def create_admin():
    if admins_collection.count_documents({}) == 0:
        admin_user = {
            'username': 'Parampara',
            'password': generate_password_hash('Parampara@risergroup'),  # Change this password!
            'created_at': datetime.now()
        }
        admins_collection.insert_one(admin_user)
        print("Admin user created: username=Parampara, password=Parampara@risergroup")

create_admin()

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            flash('Please login to access admin panel', 'warning')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# ============ PUBLIC WEBSITE ROUTES ============

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/services')
def services():
    return render_template('services.html')

@app.route('/gallery')
def gallery():
    return render_template('gallery.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

# ============ ADMIN ROUTES ============

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if 'admin_logged_in' in session:
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        admin = admins_collection.find_one({'username': username})
        
        if admin and check_password_hash(admin['password'], password):
            session['admin_logged_in'] = True
            session['admin_username'] = username
            flash('Login successful!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('admin/login.html')

@app.route('/admin/logout')
@login_required
def admin_logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('admin_login'))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    # Total submissions
    total_contacts = contacts_collection.count_documents({})
    
    # New enquiries (not contacted)
    new_enquiries = contacts_collection.count_documents({'status': {'$ne': 'contacted'}})
    
    # Latest 5 enquiries
    latest_enquiries = list(contacts_collection.find().sort('created_at', -1).limit(5))
    
    # Enquiries by event type
    pipeline = [
        {'$group': {'_id': '$eventType', 'count': {'$sum': 1}}},
        {'$sort': {'count': -1}}
    ]
    enquiries_by_type = list(contacts_collection.aggregate(pipeline))
    
    return render_template('admin/dashboard.html',
                         total_contacts=total_contacts,
                         new_enquiries=new_enquiries,
                         latest_enquiries=latest_enquiries,
                         enquiries_by_type=enquiries_by_type)

@app.route('/admin/contacts')
@login_required
def admin_contacts():
    # Get filter and sort parameters
    status_filter = request.args.get('status', 'all')
    sort_by = request.args.get('sort', 'latest')
    
    # Build query
    query = {}
    if status_filter == 'new':
        query['status'] = {'$ne': 'contacted'}
    elif status_filter == 'contacted':
        query['status'] = 'contacted'
    
    # Build sort
    if sort_by == 'latest':
        contacts = list(contacts_collection.find(query).sort('created_at', -1))
    elif sort_by == 'oldest':
        contacts = list(contacts_collection.find(query).sort('created_at', 1))
    elif sort_by == 'name':
        contacts = list(contacts_collection.find(query).sort('fullName', 1))

    
    return render_template('admin/contacts.html', 
                         contacts=contacts,
                         status_filter=status_filter,
                         sort_by=sort_by)

@app.route('/admin/contacts/delete/<contact_id>', methods=['POST'])
@login_required
def delete_contact(contact_id):
    from bson.objectid import ObjectId
    try:
        result = contacts_collection.delete_one({'_id': ObjectId(contact_id)})
        if result.deleted_count > 0:
            flash('Enquiry deleted successfully', 'success')
        else:
            flash('Enquiry not found', 'danger')
    except Exception as e:
        flash(f'Error deleting enquiry: {str(e)}', 'danger')
    
    return redirect(url_for('admin_contacts'))

@app.route('/admin/contacts/mark-contacted/<contact_id>', methods=['POST'])
@login_required
def mark_contacted(contact_id):
    from bson.objectid import ObjectId
    try:
        result = contacts_collection.update_one(
            {'_id': ObjectId(contact_id)},
            {'$set': {'status': 'contacted', 'contacted_at': datetime.now()}}
        )
        if result.modified_count > 0:
            flash('Enquiry marked as contacted', 'success')
        else:
            flash('Enquiry not found or already contacted', 'warning')
    except Exception as e:
        flash(f'Error updating enquiry: {str(e)}', 'danger')

    return redirect(url_for('admin_contacts'))

@app.route('/admin/contacts/mark-new/<contact_id>', methods=['POST'])
@login_required
def mark_new(contact_id):
    from bson.objectid import ObjectId
    try:
        result = contacts_collection.update_one(
            {'_id': ObjectId(contact_id)},
            {'$set': {'status': 'new'}, '$unset': {'contacted_at': ''}}
        )
        if result.modified_count > 0:
            flash('Enquiry marked as new', 'success')
        else:
            flash('Enquiry not found', 'warning')
    except Exception as e:
        flash(f'Error updating enquiry: {str(e)}', 'danger')
    
    return redirect(url_for('admin_contacts'))

# ============ EXISTING CONTACT FORM ROUTE ============

@app.route('/submit-contact', methods=['POST'])
def submit_contact():
    try:
        contact_data = {
            'fullName': request.form.get('fullName'),
            'phone': request.form.get('phone'),
            'email': request.form.get('email', ''),
            'eventDate': request.form.get('eventDate'),
            'eventCity': request.form.get('eventCity'),
            'eventType': request.form.get('eventType'),
            'guestCount': request.form.get('guestCount'),
            'description': request.form.get('description'),
            'status': 'new',
            'created_at': datetime.now()
        }
        
        contacts_collection.insert_one(contact_data)
        return jsonify({'success': True, 'message': 'Contact form submitted successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)