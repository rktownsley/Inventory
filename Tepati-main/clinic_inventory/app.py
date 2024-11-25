
from flask import Flask, render_template, request, redirect, url_for

import sqlite3

app = Flask(__name__)
DATABASE = 'inventory.db'

# Utility to execute queries and return results as dictionaries
def query_db(query, args=(), one=False):
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row  # This makes SQLite return rows as dictionaries
        cur = conn.cursor()
        cur.execute(query, args)
        rv = cur.fetchall()
        return (rv[0] if rv else None) if one else rv

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
                description TEXT
            );
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                value TEXT NOT NULL
            );
        ''')
        conn.commit()

# Routes
@app.route('/', methods=['GET'])
def main_page():
    search_query = request.args.get('search', '')  # Get search query from URL
    
    if search_query:
        # Search items whose name contains the search query
        items = query_db("SELECT * FROM items WHERE name LIKE ?", ('%' + search_query + '%',))
    else:
        items = query_db("SELECT * FROM items")  # Get all items if no search query
    
    return render_template('main.html', items=items)


@app.route('/add', methods=['GET', 'POST'])
def add_item():
    if request.method == 'POST':
        name = request.form['name']
        quantity = request.form['quantity']
        location = request.form['location']
        category = request.form['category']
        description = request.form['description']
        query_db("INSERT INTO items (name, quantity, location, category, description) VALUES (?, ?, ?, ?, ?)",
                 [name, quantity, location, category, description])
        return redirect(url_for('main_page'))
    locations = query_db("SELECT value FROM settings WHERE type = 'location'")
    categories = query_db("SELECT value FROM settings WHERE type = 'category'")
    return render_template('add_item.html', locations=locations, categories=categories)

@app.route('/view/<int:item_id>', methods=['GET', 'POST'])
def view_item(item_id):
    item = query_db("SELECT * FROM items WHERE id = ?", [item_id], one=True)
    if request.method == 'POST':
        name = request.form['name']
        quantity = request.form['quantity']
        location = request.form['location']
        category = request.form['category']
        description = request.form['description']
        query_db("UPDATE items SET name = ?, quantity = ?, location = ?, category = ?, description = ? WHERE id = ?",
                 [name, quantity, location, category, description, item_id])
        return redirect(url_for('main_page'))
    locations = query_db("SELECT value FROM settings WHERE type = 'location'")
    categories = query_db("SELECT value FROM settings WHERE type = 'category'")
    return render_template('view_item.html', item=item, locations=locations, categories=categories)

@app.route('/delete/<int:item_id>')
def delete_item(item_id):
    query_db("DELETE FROM items WHERE id = ?", [item_id])
    return redirect(url_for('main_page'))

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        setting_type = request.form['type']
        value = request.form['value']
        # Handle adding new locations or categories
        query_db("INSERT INTO settings (type, value) VALUES (?, ?)", [setting_type, value])
        return redirect(url_for('settings'))
    
    # Get locations and categories
    locations = query_db("SELECT value FROM settings WHERE type = 'location'")
    categories = query_db("SELECT value FROM settings WHERE type = 'category'")
    return render_template('settings.html', locations=locations, categories=categories)

@app.route('/delete_location/<location_value>', methods=['POST'])
def delete_location(location_value):
    query_db("DELETE FROM settings WHERE type = 'location' AND value = ?", [location_value])
    return redirect(url_for('settings'))

@app.route('/delete_category/<category_value>', methods=['POST'])
def delete_category(category_value):
    query_db("DELETE FROM settings WHERE type = 'category' AND value = ?", [category_value])
    return redirect(url_for('settings'))

@app.route('/edit_item/<int:item_id>', methods=['GET', 'POST'])
def edit_item(item_id):
    item = query_db("SELECT * FROM items WHERE id = ?", [item_id], one=True)
    if request.method == 'POST':
        name = request.form['name']
        quantity = request.form['quantity']
        location = request.form['location']
        category = request.form['category']
        description = request.form['description']
        query_db("UPDATE items SET name = ?, quantity = ?, location = ?, category = ?, description = ? WHERE id = ?",
                 [name, quantity, location, category, description, item_id])
        return redirect(url_for('view_item', item_id=item_id))  # Redirect back to the view page

    # Retrieve available locations and categories for the form
    locations = query_db("SELECT value FROM settings WHERE type = 'location'")
    categories = query_db("SELECT value FROM settings WHERE type = 'category'")

    return render_template('edit_item.html', item=item, locations=locations, categories=categories)

@app.route('/use_item/<int:item_id>', methods=['GET', 'POST'])
def use_item(item_id):
    item = query_db('SELECT * FROM items WHERE id = ?', [item_id], one=True)
    
    if item is None:
        flash('Item not found', 'error')
        return redirect(url_for('home'))  # Or wherever you want to go if item not found
    
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
            return redirect(url_for('view_item', item_id=item_id))
        else:
            flash('Not enough quantity available', 'error')
            return render_template('use_item.html', item=item)  # Show an error if quantity used is too high

    return render_template('use_item.html', item=item)

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
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5001)

