
from flask import Flask, flash, render_template, request, redirect, url_for, session, jsonify

import sqlite3

import os
from werkzeug.utils import secure_filename

# Define allowed extensions
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS



app = Flask(__name__)
DATABASE = 'inventory.db'
# Define where the uploaded photos are stored
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')

# Utility to execute queries and return results as dictionaries
def query_db(query, args=(), one=False):
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row  # This makes SQLite return rows as dictionaries
        cur = conn.cursor()
        cur.execute(query, args)
        rv = cur.fetchall()
        return (rv[0] if rv else None) if one else rv

# Initialize database
# Initialize database
def init_db():
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.executescript('''
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                location TEXT,
                category TEXT,
                description TEXT,
                instrument_type TEXT, 
                expiration_date TEXT, 
                supplier TEXT, 
                dosage TEXT, 
                form TEXT, 
                lot_number TEXT, 
                ndc TEXT, 
                dispense_used INTEGER, 
                unit_quantity INTEGER, 
                prescription_type TEXT,
                minimum_supply INTEGER, -- Added column for minimum supply before photo_url
                photo_url TEXT          -- Added column for photo URL
            );
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                value TEXT NOT NULL
            );
        ''')
        conn.commit()






# Check if the user is logged in and is admin
def is_admin():
    return session.get('user') == 'admin'

# Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Hardcoded check for simplicity
        if username == 'admin' and password == 'adminpassword':
            session['user'] = 'admin'  # Store the username in session
            return redirect(url_for('main_page'))  # Redirect to the main page
        elif username == 'user1' and password == 'password1':
            session['user'] = 'user1'  # Store the username in session
            return redirect(url_for('main_page'))  # Redirect to the main page
        elif username == 'tepati' and password == 'tepati71':
            session['user'] = 'tepati'  # Store the username in session
            return redirect(url_for('main_page', location='Tepati'))  # Redirect to the main page
        elif username == 'KLOHC' and password == 'KLOHC1':
            session['user'] = 'klohc'  # Store the username in session
            return redirect(url_for('main_page', location="Knights Landing"))  # Redirect to the main page
        else:
            flash('Invalid username or password', 'error')
            return redirect(url_for('login'))
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)  # Remove the user from the session
    return redirect(url_for('login'))





# Routes
@app.route('/', methods=['GET'])
def main_page():
    if not session.get('user'):
        return redirect(url_for('login'))
    
    search_query = request.args.get('search', '')  # Get search query from URL
    location_filter = request.args.get('location', '')  # Get selected location from URL
    
    # Base query to get all items
    query = "SELECT * FROM items WHERE 1=1"
    params = []
    
    # Apply search filter if search query exists
    if search_query:
        query += " AND name LIKE ?"
        params.append('%' + search_query + '%')
    
    # Apply location filter if a location is selected
    if location_filter:
        query += " AND location = ?"
        params.append(location_filter)

    
    # Add order by clause to show the most recent items first
    query += " ORDER BY id DESC"


    # Fetch filtered items based on the query
    items = query_db(query, params)
    
    # Fetch locations for the dropdown (assuming you're using the 'settings' table for locations)
    locations = query_db("SELECT value FROM settings WHERE type = 'location'")
    
    return render_template('main.html', items=items, locations=locations)



@app.route('/add', methods=['GET', 'POST'])
def add_item():
    search_query = request.args.get('search', '')
    location_filter = request.args.get('location', '')

    if request.method == 'POST':
        # Basic fields
        name = request.form['name'].strip()
        quantity = int(request.form['quantity'])
        location = request.form['location'].strip()
        category = request.form['category'].strip()
        description = request.form['description'].strip()

        # Photo handling (as before)
        photo_url = None
        if 'photo' in request.files:
            file = request.files['photo']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join('static/uploads', filename))
                photo_url = f'uploads/{filename}'

        # Medication-specific fields (default to empty strings to avoid NULL)
        fields = ['instrument_type', 'expiration_date', 'supplier', 'dosage', 'form', 
                  'lot_number', 'ndc', 'dispense_used', 'unit_quantity', 'prescription_type']
        form_data = {field: request.form.get(field, '').strip() for field in fields}

        # Minimum supply (ensure integer or default to 0)
        #minimum_supply = int(request.form.get('minimum_supply', 0))
        # Ensure minimum_supply defaults to 0 if left blank
        minimum_supply = request.form.get('minimum_supply', '').strip()
        if minimum_supply == '' or not minimum_supply.isdigit():
            minimum_supply = 0  # Default to 0 if the field is empty or not a valid number
        else:
            minimum_supply = int(minimum_supply)

        # Check for an existing item with identical attributes
        existing_item = query_db("""
            SELECT * FROM items WHERE name = ? AND location = ? AND category = ? 
            AND IFNULL(expiration_date, '') = ? AND IFNULL(supplier, '') = ?
            AND IFNULL(dosage, '') = ? AND IFNULL(form, '') = ? AND IFNULL(lot_number, '') = ?
            AND IFNULL(ndc, '') = ? AND IFNULL(dispense_used, '') = ? AND IFNULL(unit_quantity, '') = ?
            AND IFNULL(prescription_type, '') = ? AND IFNULL(instrument_type, '') = ?
        """, [name, location, category, form_data['expiration_date'], form_data['supplier'], 
              form_data['dosage'], form_data['form'], form_data['lot_number'], form_data['ndc'], 
              form_data['dispense_used'], form_data['unit_quantity'], form_data['prescription_type'], 
              form_data['instrument_type']], one=True)

        if existing_item:
            # Update the quantity if item exists
            query_db("UPDATE items SET quantity = quantity + ? WHERE id = ?", 
                     [quantity, existing_item['id']])
        else:
            # Insert new item
            query_db("""
                INSERT INTO items (name, quantity, location, category, description, photo_url, instrument_type,
                                   expiration_date, supplier, dosage, form, lot_number, ndc, dispense_used, 
                                   unit_quantity, prescription_type, minimum_supply)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [name, quantity, location, category, description, photo_url, form_data['instrument_type'],
                  form_data['expiration_date'], form_data['supplier'], form_data['dosage'], form_data['form'],
                  form_data['lot_number'], form_data['ndc'], form_data['dispense_used'], 
                  form_data['unit_quantity'], form_data['prescription_type'], minimum_supply])

        return redirect(url_for('main_page', search=search_query, location=location_filter))

    locations = query_db("SELECT value FROM settings WHERE type = 'location'")
    categories = query_db("SELECT value FROM settings WHERE type = 'category'")
    return render_template('add_item.html', locations=locations, categories=categories, search=search_query, location=location_filter)






@app.route('/view/<int:item_id>', methods=['GET', 'POST'])
def view_item(item_id):
    item = query_db("SELECT * FROM items WHERE id = ?", [item_id], one=True)

    search_query = request.args.get('search', '')  # Get search query from URL
    location_filter = request.args.get('location', '')  # Get selected location from URL

    if request.method == 'POST':
        # Basic fields
        name = request.form['name']
        quantity = request.form['quantity']
        location = request.form['location']
        category = request.form['category']
        description = request.form['description']
        minimum_supply = request.form['minimum_supply']  # New field for minimum supply
        
        photo_url = None  # Default to None if no photo is uploaded
        # Handle file upload (if any)
        if 'photo' in request.files:
            file = request.files['photo']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                print(f"Saving file: {filename}")  # Debugging
                file.save(os.path.join('static/uploads', filename))
                photo_url = f'uploads/{filename}'  # Path relative to static folder
            else:
                print("File not allowed or no file provided.")
        else:
            print("No file uploaded.")

        # New fields (medication/surgical instrument specific)
        instrument_type = request.form.get('instrument_type', None)
        expiration_date = request.form.get('expiration_date', None)
        supplier = request.form.get('supplier', None)
        dosage = request.form.get('dosage', None)
        form = request.form.get('form', None)
        lot_number = request.form.get('lot_number', None)
        ndc = request.form.get('ndc', None)
        dispense_used = request.form.get('dispense_used', None)
        unit_quantity = request.form.get('unit_quantity', None)
        prescription_type = request.form.get('prescription_type', None)
        
        # Update the database, including the minimum supply field
        query_db("""
            UPDATE items SET 
            name = ?, quantity = ?, location = ?, category = ?, description = ?, 
            photo_url = ?, instrument_type = ?, expiration_date = ?, supplier = ?, dosage = ?, form = ?, 
            lot_number = ?, ndc = ?, dispense_used = ?, unit_quantity = ?, prescription_type = ?, minimum_supply = ? 
            WHERE id = ?
        """, [name, quantity, location, category, description, photo_url, instrument_type, expiration_date, 
              supplier, dosage, form, lot_number, ndc, dispense_used, unit_quantity, prescription_type, minimum_supply, item_id])


        # After updating, redirect back to the main page with the search and location query parameters

        return redirect(url_for('main_page', search=search_query, location=location_filter))
        #return redirect(url_for('main_page'))

    # Fetch locations and categories for dropdowns
    locations = query_db("SELECT value FROM settings WHERE type = 'location'")
    categories = query_db("SELECT value FROM settings WHERE type = 'category'")

    return render_template('view_item.html', item=item, locations=locations, categories=categories, search=search_query, location=location_filter)







@app.route('/delete/<int:item_id>')
def delete_item(item_id):
    # Fetch the photo URL from the database
    item = query_db("SELECT photo_url FROM items WHERE id = ?", [item_id], one=True)
    
    if item and item['photo_url']:
        photo_path = os.path.join('static', item['photo_url'])
        if os.path.exists(photo_path):
            os.remove(photo_path)
    
    # Delete the item from the database
    query_db("DELETE FROM items WHERE id = ?", [item_id])

    search_query = request.args.get('search', '')  # Get search query from URL
    location_filter = request.args.get('location', '')  # Get selected location from URL
    
    return redirect(url_for('main_page', search=search_query, location=location_filter))

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        setting_type = request.form.get('type')
        value = request.form.get('value', '').strip()  # Trim any whitespace
        
        # Server-side validation to ensure no empty or whitespace-only submissions
        if not value:
            flash('Field cannot be empty', 'error')
            return redirect(url_for('settings'))
        
        # Check for duplicates before inserting (location or category)
        existing_item = query_db(
            "SELECT * FROM settings WHERE type = ? AND value = ?", [setting_type, value], one=True
        )
        if existing_item:
            flash(f'{setting_type.capitalize()} "{value}" already exists!', 'warning')
        else:
            # Insert into the database only if valid
            query_db("INSERT INTO settings (type, value) VALUES (?, ?)", [setting_type, value])
            flash(f'{setting_type.capitalize()} "{value}" added successfully!', 'success')

        return redirect(url_for('settings'))

    # Fetch all locations and categories from the database
    locations = query_db("SELECT value FROM settings WHERE type = 'location'")
    categories = query_db("SELECT value FROM settings WHERE type = 'category'")
    
    return render_template('settings.html', locations=locations, categories=categories)


@app.route('/delete_location/<location_value>', methods=['POST'])
def delete_location(location_value):
    # Fetch the name of the location being deleted
    location_name = query_db("SELECT value FROM settings WHERE type = 'location' AND value = ?", [location_value], one=True)
    
    if location_name:
        # Delete the location entry that matches the 'value' field
        query_db("DELETE FROM settings WHERE type = 'location' AND value = ?", [location_value])
        flash(f'Location "{location_value}" deleted successfully!', 'success')
    else:
        flash('Location not found!', 'error')

    return redirect(url_for('settings'))


@app.route('/delete_category/<category_value>', methods=['POST'])
def delete_category(category_value):
    # Fetch the name of the category being deleted
    category_name = query_db("SELECT value FROM settings WHERE type = 'category' AND value = ?", [category_value], one=True)
    
    if category_name:
        # Delete the category entry that matches the 'value' field
        query_db("DELETE FROM settings WHERE type = 'category' AND value = ?", [category_value])
        flash(f'Category "{category_value}" deleted successfully!', 'success')
    else:
        flash('Category not found!', 'error')

    return redirect(url_for('settings'))




@app.route('/edit_item/<int:item_id>', methods=['GET', 'POST'])
def edit_item(item_id):
    item = query_db("SELECT * FROM items WHERE id = ?", [item_id], one=True)

    search_query = request.args.get('search', '')  # Get search query from URL
    location_filter = request.args.get('location', '')  # Get selected location from URL

    if request.method == 'POST':
        # Basic fields
        name = request.form['name']
        quantity = request.form['quantity']
        location = request.form['location']
        category = request.form['category']
        description = request.form['description']
        minimum_supply = request.form['minimum_supply']  # New field for minimum supply
        
        photo_url = None  # Default to None if no photo is uploaded

        # Initialize photo_url with current photo (in case no new photo is uploaded)
        photo_url = item['photo_url']

        # Handle file upload
        if 'item_photo' in request.files:
            file = request.files['item_photo']
            if file and allowed_file(file.filename):  # Check file type
                filename = secure_filename(file.filename)
                file.save(os.path.join('static/uploads', filename))
                photo_url = f'uploads/{filename}'  # Update photo_url with new file path

        # New fields (medication/surgical instrument specific)
        instrument_type = request.form.get('instrument_type', None)  # For surgical instruments
        expiration_date = request.form.get('expiration_date', None)  # For medications
        supplier = request.form.get('supplier', None)  # For medications
        dosage = request.form.get('dosage', None)  # For medications
        form = request.form.get('form', None)  # For medications
        lot_number = request.form.get('lot_number', None)  # For medications
        ndc = request.form.get('ndc', None)  # For medications
        dispense_used = request.form.get('dispense_used', None)  # For medications
        unit_quantity = request.form.get('unit_quantity', None)  # For medications
        prescription_type = request.form.get('prescription_type', None)  # For medications
        
        # Update the database with all the fields, including minimum_supply and photo_url
        query_db("""
            UPDATE items SET 
            name = ?, quantity = ?, location = ?, category = ?, description = ?, 
            photo_url = ?, instrument_type = ?, expiration_date = ?, supplier = ?, dosage = ?, form = ?, 
            lot_number = ?, ndc = ?, dispense_used = ?, unit_quantity = ?, prescription_type = ?, minimum_supply = ? 
            WHERE id = ?
        """, [name, quantity, location, category, description, photo_url, instrument_type, expiration_date, 
              supplier, dosage, form, lot_number, ndc, dispense_used, unit_quantity, prescription_type, minimum_supply, item_id])

        return redirect(url_for('view_item', item_id=item_id, search=search_query, location=location_filter))
        #return redirect(url_for('view_item', item_id=item_id))  # Redirect back to the view page

    # Retrieve available locations and categories for the form
    locations = query_db("SELECT value FROM settings WHERE type = 'location'")
    categories = query_db("SELECT value FROM settings WHERE type = 'category'")

    return render_template('edit_item.html', item=item, locations=locations, categories=categories, search=search_query, location=location_filter)



@app.route('/delete_photo', methods=['DELETE'])
def delete_photo():
    data = request.get_json()  # Get the JSON data from the request body
    photo_url = data.get("photo_url")
    
    if not photo_url:
        return jsonify({"error": "Photo URL is required"}), 400
    
    # Construct the path to the photo file
    photo_path = os.path.join(app.config['UPLOAD_FOLDER'], photo_url)
    
    # Check if the photo exists and delete it
    if os.path.exists(photo_path):
        os.remove(photo_path)  # Delete the file from the server
        return jsonify({"message": "Photo deleted successfully"}), 200
    else:
        return jsonify({"error": "Photo not found"}), 404






@app.route('/use_item/<int:item_id>', methods=['GET', 'POST'])
def use_item(item_id):
    item = query_db('SELECT * FROM items WHERE id = ?', [item_id], one=True)

    search_query = request.args.get('search', '')  # Get search query from URL
    location_filter = request.args.get('location', '')  # Get selected location from URL
    
    if item is None:
        flash('Item not found', 'error')
        return redirect(url_for('home', search=search_query, location=location_filter))  # Or wherever you want to go if item not found
    
    if request.method == 'POST':
        quantity_used = int(request.form['quantity_used'])
        
        # Check if the quantity used is greater than the available quantity
        if quantity_used <= item['quantity']:
            new_quantity = item['quantity'] - quantity_used
            
            # Update the item's quantity in the database
            query_db('UPDATE items SET quantity = ? WHERE id = ?', [new_quantity, item_id])
            
            # Access min_level safely by checking if it exists
            min_level = item['min_level'] if 'min_level' in item else None
            
            # Check if the min_level is present and if quantity is below the minimum level
            if min_level is not None and new_quantity <= min_level:
                flash('Warning: Quantity below minimum level', 'warning')
            
            # Redirect back to the item details page after successful update
            return redirect(url_for('view_item', item_id=item_id, search=search_query, location=location_filter))
        else:
            flash('Not enough quantity available', 'error')
            return render_template('use_item.html', item=item, search=search_query, location=location_filter)  # Show an error if quantity used is too high

    return render_template('use_item.html', item=item, search=search_query, location=location_filter)



@app.route('/transfer_item/<int:item_id>', methods=['POST'])
def transfer_item(item_id):
    search_query = request.args.get('search', '')
    location_filter = request.args.get('location', '')

    item = query_db("SELECT * FROM items WHERE id = ?", [item_id], one=True)

    if not item:
        flash('Item not found', 'error')
        return redirect(url_for('main_page', search=search_query, location=location_filter))

    quantity_to_transfer = int(request.form['quantity_to_transfer'])
    new_location = request.form['new_location'].strip()

    if quantity_to_transfer > item['quantity']:
        flash('Cannot transfer more than the available quantity', 'error')
        return redirect(url_for('view_item', item_id=item_id, search=search_query, location=location_filter))

    query_db("UPDATE items SET quantity = quantity - ? WHERE id = ?", [quantity_to_transfer, item_id])

    # Check for existing item in new location with identical fields
    existing_item = query_db("""
        SELECT * FROM items WHERE name = ? AND location = ? AND category = ?
        AND IFNULL(expiration_date, '') = ? AND IFNULL(supplier, '') = ?
        AND IFNULL(dosage, '') = ? AND IFNULL(form, '') = ? AND IFNULL(lot_number, '') = ?
        AND IFNULL(ndc, '') = ? AND IFNULL(dispense_used, '') = ? AND IFNULL(unit_quantity, '') = ?
        AND IFNULL(prescription_type, '') = ? AND IFNULL(instrument_type, '') = ?
    """, [item['name'], new_location, item['category'], item['expiration_date'], item['supplier'],
          item['dosage'], item['form'], item['lot_number'], item['ndc'], item['dispense_used'],
          item['unit_quantity'], item['prescription_type'], item['instrument_type']], one=True)

    if existing_item:
        query_db("UPDATE items SET quantity = quantity + ? WHERE id = ?", 
                 [quantity_to_transfer, existing_item['id']])
    else:
        query_db("""
            INSERT INTO items (name, quantity, location, category, description, photo_url, instrument_type,
                               expiration_date, supplier, dosage, form, lot_number, ndc, dispense_used, 
                               unit_quantity, prescription_type, minimum_supply)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [item['name'], quantity_to_transfer, new_location, item['category'], item['description'], 
              item['photo_url'], item['instrument_type'], item['expiration_date'], item['supplier'], 
              item['dosage'], item['form'], item['lot_number'], item['ndc'], item['dispense_used'], 
              item['unit_quantity'], item['prescription_type'], item['minimum_supply']])

    flash(f"Successfully transferred {quantity_to_transfer} of {item['name']} to {new_location}", 'success')
    return redirect(url_for('main_page', search=search_query, location=location_filter))






@app.route('/autocomplete', methods=['GET'])
def autocomplete():
    search_query = request.args.get('query', '')  # Get the query parameter from the GET request
    print(f"Searching for: {search_query}")  # Debugging line
    suggestions = query_db("SELECT name FROM items WHERE name LIKE ?", ('%' + search_query + '%',))
    names = [suggestion['name'] for suggestion in suggestions]  # Extract names from the result
    print(f"Suggestions: {names}")  # Debugging line
    return {'suggestions': names}

# Clean up empty locations and categories from the database
def clean_empty_values():
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        # Delete empty location and category entries
        cur.execute("DELETE FROM settings WHERE value = '' OR value IS NULL")
        conn.commit()



if __name__ == '__main__':
    clean_empty_values()  # Clean up empty entries before starting the app
    app.secret_key = 'your_secret_key_here'  # Replace with a secure random string in production
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5001)

