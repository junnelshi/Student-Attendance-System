from flask import (
    Flask, render_template, redirect, url_for, request, session, flash, 
    jsonify, send_file, make_response
)
from dbhelper import (
    init_database, getone, getall, addrecord, updaterecord, deleterecord, recordexists,
    recordexists_exclude,
    get_user_by_email, get_all_users, delete_user, get_student_by_idno,
    record_attendance, get_attendance_by_date, get_attendance_today
)
from werkzeug.security import generate_password_hash, check_password_hash
import qrcode
import qrcode.constants 
import io
from io import BytesIO 
import base64
import os
from datetime import datetime
import traceback 
import json

app = Flask(__name__)
app.secret_key = 'your-secret-key-here-change-this'
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Disable caching for development

# IMPORTANT: UPLOAD_FOLDER is for STUDENT IMAGES ONLY
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'static', 'images')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Use Flask route to serve the actual default icon file
DEFAULT_ICON = '/default-icon'

init_database()

def rows_to_dicts(rows):
    return [dict(row) for row in rows]

def row_to_dict(row):
    return dict(row) if row else None

def get_user_by_id(user_id):
    return getone('users', id=user_id)


# Utilities

def generate_qr_code_image(idno):
    """
    Generate QR code image.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H, 
        box_size=10, 
        border=4,
    )
    qr.add_data(idno)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    return img

def generate_qr_code_uri(idno):
    """Generate QR code as data URI"""
    qr_img = generate_qr_code_image(idno)
    buffered = io.BytesIO()
    qr_img.save(buffered, format="WEBP")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return f"data:image/webp;base64,{img_str}"


# Routes
# Routes
# Routes

@app.route("/")
def index():
    """Automatically redirect to QR scanner page"""
    return redirect(url_for('qr_scanner'))

@app.route('/home')
def home():
    """Redirect home to QR scanner as well"""
    return redirect(url_for('qr_scanner'))

@app.route("/qr-scanner")
def qr_scanner():
    return render_template("qr_scanner.html")

@app.route('/scanned-profile')
def show_scanned_profile():
    """
    Fetches student data based on 'idno' and applies 
    cache control headers correctly using make_response().
    """
    # 1. Get idno from query parameters 
    idno = request.args.get('idno')
    
    if not idno:
        flash("Error: No student ID provided for scanning.", "error")
        response = make_response(redirect(url_for('qr_scanner')))
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    
    # 2. Fetch the student from the database
    student_row = get_student_by_idno(idno)
    student = row_to_dict(student_row)
    
    if not student:
        flash(f"Student with ID No. {idno} not found.", "warning")
        response = make_response(redirect(url_for('qr_scanner')))
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response

    # 3. Handle the student's image URL
    filename = student.get('image_filename')
    image_path = os.path.join(UPLOAD_FOLDER, filename) if filename else None
    
    if filename and os.path.exists(image_path):
        student['image_url'] = url_for('static', filename=f'images/{filename}')
    else:
        student['image_url'] = DEFAULT_ICON 

    # 4. Render the template and wrap it in a Response object
    rendered_html = render_template('scanned_profile.html', student=student)
    response = make_response(rendered_html)
    
    # 5. CRITICAL FIX: Set no-cache headers on the Response object
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    # 6. Return the fully formed Response object
    return response

@app.route("/login", methods=['GET', 'POST'])
def login():
    """
    Admin login
    """
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = get_user_by_email(email)

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['user_email'] = user['email']
            return redirect(url_for('user_management') + '?login_success=true')

        return redirect(url_for('login') + '?error=true')

    return render_template("login.html")

@app.route("/logout")
def logout():
    """Logout user"""
    session.clear() 
    return redirect(url_for('login') + '?logout=true')

@app.route("/user-management", methods=['GET', 'POST'])
def user_management():
    if 'user_id' not in session:
        return redirect(url_for('login') + '?timeout=true')

    if request.method == 'POST':
        user_id_to_update = request.form.get('id')
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')

        if not all([name, email]):
            flash('Name and Email are required.', 'error')
            return redirect(url_for('user_management'))

        
# --- UPDATE USER ---

        if user_id_to_update:
            existing = getone('users', email=email)
            if existing and str(existing['id']) != str(user_id_to_update):
                flash("Another user with this email already exists!", "warning")
                return redirect(url_for('user_management'))

            update_kwargs = {'name': name, 'email': email}
            if password and password.strip():
                update_kwargs['password'] = generate_password_hash(password)

            if updaterecord('users', 'id', user_id_to_update, **update_kwargs):
                flash("User updated successfully!", "success")
            else:
                flash("Error updating user.", "error")

# --- ADD NEW USER ---

        else:
            if not password or not password.strip():
                flash('Password is required for new users.', 'error')
                return redirect(url_for('user_management'))

            if recordexists('users', email=email):
                flash("User with this email already exists!", "warning")
                return redirect(url_for('user_management'))

            hashed = generate_password_hash(password)
            if addrecord('users', name=name, email=email, password=hashed):
                flash("User added successfully!", "success")
            else:
                flash("Failed to save user.", "error")

        return redirect(url_for('user_management'))

    users = rows_to_dicts(get_all_users())
    return render_template("user_management.html", users=users)

@app.route("/edit-user/<int:user_id>")
def edit_user(user_id):
    if 'user_id' not in session:
        return redirect(url_for('login') + '?timeout=true')
    
    user_to_edit = row_to_dict(get_user_by_id(user_id)) 
    
    if not user_to_edit:
        return redirect(url_for('user_management') + '?user_action_error=user_not_found')
    
    users = rows_to_dicts(get_all_users())
    return render_template("user_management.html", users=users, user_to_edit=user_to_edit)


@app.route("/delete-user/<int:user_id>")
def delete_user_route(user_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if delete_user(user_id):
        # AUTO-RESET: Reset ID counter after deletion
        try:
            conn = __import__('dbhelper').connect()
            cur = conn.cursor()
            cur.execute("SELECT MAX(id) FROM users")
            max_id = cur.fetchone()[0]
            
            if max_id:
                cur.execute("DELETE FROM sqlite_sequence WHERE name='users'")
                cur.execute("INSERT INTO sqlite_sequence (name, seq) VALUES ('users', ?)", (max_id,))
                conn.commit()
                print(f"[AUTO-RESET] User ID counter reset to {max_id}")
            
            conn.close()
        except Exception as e:
            print(f"Error auto-resetting user ID: {e}")
        
        return redirect(url_for('user_management') + '?user_deleted=true')
    else:
        return redirect(url_for('user_management') + '?user_action_error=delete_failed')

@app.route("/reset-user-id")
def reset_user_id():
    """Manual reset users table auto-increment counter to latest ID"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        conn = __import__('dbhelper').connect()
        cur = conn.cursor()
        
        # Get the maximum ID from users table
        cur.execute("SELECT MAX(id) FROM users")
        max_id = cur.fetchone()[0]
        
        if max_id is None:
            flash("No users found.", "warning")
            return redirect(url_for('user_management'))
        
        # Delete the old sequence entry and insert new one
        cur.execute("DELETE FROM sqlite_sequence WHERE name='users'")
        cur.execute("INSERT INTO sqlite_sequence (name, seq) VALUES ('users', ?)", (max_id,))
        conn.commit()
        
        flash(f"User ID counter reset successfully! Next ID will be {max_id + 1}.", "success")
        print(f"[RESET] User auto-increment reset to {max_id}")
        
    except Exception as e:
        print(f"Error resetting user ID: {e}")
        flash(f"Error resetting ID counter: {e}", "error")
    finally:
        conn.close()
    
    return redirect(url_for('user_management'))

@app.route("/student-management")
def student_management():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    students = rows_to_dicts(getall('students'))

    try:
        students.sort(key=lambda x: int(x.get('idno', '0')))
    except ValueError:
        pass

    for student in students:
        filename = student.get('image_filename')
        if filename and os.path.exists(os.path.join(UPLOAD_FOLDER, filename)):
            student['image_url'] = url_for('static', filename=f'images/{filename}')
        else:
            student['image_url'] = DEFAULT_ICON

    return render_template("student_management.html", students=students)

@app.route("/delete-student/<idno>")
def delete_student(idno):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    student = row_to_dict(get_student_by_idno(idno))
    if deleterecord('students', idno=idno):
        conn = __import__('dbhelper').connect()
        cur = conn.cursor()
        try:
            cur.execute("DELETE FROM attendance WHERE idno=?", (idno,))
            conn.commit()
            deleted_count = cur.rowcount
            if deleted_count > 0:
                print(f"[CLEANUP] Deleted {deleted_count} attendance records for student {idno}")
        except Exception as e:
            print(f"Error deleting attendance records: {e}")
        finally:
            conn.close()
        
        if student and student.get('image_filename'):
            filepath = os.path.join(UPLOAD_FOLDER, student['image_filename'])
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
            except Exception as e:
                print("Error deleting image file:", e)
        
        flash("Student and all associated attendance records deleted.", "success") 
    else:
        flash("Error deleting student.", "error")

    return redirect(url_for('student_management'))

@app.route("/camera-viewer")
def camera_viewer():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    update_idno = request.args.get('update_idno')
    student_data = None
    if update_idno:
        student_data = row_to_dict(get_student_by_idno(update_idno))
        if student_data:
            filename = student_data.get('image_filename')
            if filename and os.path.exists(os.path.join(UPLOAD_FOLDER, filename)):
                student_data['image_url'] = url_for('static', filename=f'images/{filename}')
            else:
                student_data['image_url'] = DEFAULT_ICON
    
    return render_template("camera_viewer.html", update_idno=update_idno, student=student_data)

@app.route("/save_student", methods=['POST'])
def save_student():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    update_idno = request.form.get('update_idno')
    old_idno = request.form.get('old_idno') or update_idno
    idno = request.form.get('idno')
    lastname = request.form.get('lastname')
    firstname = request.form.get('firstname')
    course = request.form.get('course')
    level = request.form.get('level')
    webcam_image_data = request.form.get('webcam_image_data')

    if not all([idno, lastname, firstname, course, level]):
        flash('All student fields are required.', 'error')
        if update_idno:
            return redirect(url_for('camera_viewer', update_idno=update_idno))
        return redirect(url_for('camera_viewer'))

    if update_idno:
        existing_student = row_to_dict(get_student_by_idno(update_idno))
        if not existing_student:
            flash("Original student record not found.", "error")
            return redirect(url_for('student_management'))

        if idno != update_idno:
            if recordexists_exclude('students', 'idno', idno, 'idno', update_idno):
                flash(f"ID {idno} already exists. Choose a different ID.", "error")
                return redirect(url_for('camera_viewer', update_idno=update_idno))

        new_filename = None
        filepath = None

        if webcam_image_data and webcam_image_data.strip():
            try:
                base64_image = webcam_image_data.split(',')[1] if ',' in webcam_image_data else webcam_image_data
                image_bytes = base64.b64decode(base64_image)

                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                new_filename = f"{idno}_{timestamp}.jpg"
                filepath = os.path.join(UPLOAD_FOLDER, new_filename)

                with open(filepath, 'wb') as f:
                    f.write(image_bytes)
            except Exception as e:
                flash(f"Error saving new image: {e}", "error")
                return redirect(url_for('camera_viewer', update_idno=update_idno))

        update_kwargs = {
            'idno': idno,
            'lastname': lastname,
            'firstname': firstname,
            'course': course,
            'level': level
        }
        if new_filename:
            update_kwargs['image_filename'] = new_filename

        if updaterecord('students', 'idno', update_idno, **update_kwargs):
            if idno != update_idno:
                conn = __import__('dbhelper').connect()
                cur = conn.cursor()
                try:
                    cur.execute("UPDATE attendance SET idno=? WHERE idno=?", (idno, update_idno))
                    conn.commit()
                    print(f"Updated attendance records from {update_idno} to {idno}")
                except Exception as e:
                    print(f"Error updating attendance records: {e}")
                finally:
                    conn.close()
            
            if new_filename and existing_student.get('image_filename'):
                old_filepath = os.path.join(UPLOAD_FOLDER, existing_student['image_filename'])
                try:
                    if os.path.exists(old_filepath):
                        os.remove(old_filepath)
                except Exception as e:
                    print(f"Error removing old image: {e}")

            flash("Student updated successfully!", "success")
            return redirect(url_for('student_management'))
        else:
            if filepath and os.path.exists(filepath):
                os.remove(filepath)
            flash("Database error updating student.", "error")
            return redirect(url_for('camera_viewer', update_idno=update_idno))
    else:
        if recordexists('students', idno=idno):
            flash(f"ID {idno} already exists.", 'error')
            return redirect(url_for('camera_viewer'))

        if not webcam_image_data or not webcam_image_data.strip():
            flash('Snapshot required for new student.', 'error')
            return redirect(url_for('camera_viewer'))

        try:
            base64_image = webcam_image_data.split(',')[1] if ',' in webcam_image_data else webcam_image_data
            image_bytes = base64.b64decode(base64_image)

            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            filename = f"{idno}_{timestamp}.jpg"
            filepath = os.path.join(UPLOAD_FOLDER, filename)

            with open(filepath, 'wb') as f:
                f.write(image_bytes)
        except Exception as e:
            flash(f"Error saving image: {e}", "error")
            return redirect(url_for('camera_viewer'))

        if addrecord('students', idno=idno, lastname=lastname, firstname=firstname,
                     course=course, level=level, image_filename=filename):
            flash("Student saved successfully!", "success")
            return redirect(url_for('student_management'))

        if os.path.exists(filepath):
            os.remove(filepath)
        flash("Database error saving student.", "error")
        return redirect(url_for('camera_viewer'))

@app.route("/view-attendance")
def view_attendance():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    selected_date = request.args.get('date')
    
    if selected_date:
        try:
            parsed_date = datetime.strptime(selected_date, "%Y-%m-%d")
            selected_date = parsed_date.strftime("%Y-%m-%d")
        except ValueError:
            selected_date = datetime.now().strftime("%Y-%m-%d")
    else:
        selected_date = datetime.now().strftime("%Y-%m-%d")
    
    records = rows_to_dicts(get_attendance_by_date(selected_date))

    for record in records:
        time_24h = record.get('time_in')
        if time_24h:
            try:
                time_to_parse = time_24h.split('.')[0]
                time_obj = datetime.strptime(time_to_parse, "%H:%M:%S")
                time_12h = time_obj.strftime("%I:%M %p").lstrip('0')
                record['time_in'] = time_12h
            except ValueError:
                pass 
    
    return render_template("view_attendance.html", records=records, selected_date=selected_date)

@app.route("/scan-attendance", methods=['POST'])
def scan_attendance():
    """
    Processes QR scan and records attendance. 
    Ensures time is displayed as H:M AM/PM without seconds.
    """
    idno = None

    try:
        data = request.get_json(silent=True) 
        if data and 'idno' in data:
            idno = data.get('idno')
        
        if not idno:
            raw_data = request.data.decode('utf-8')
            if raw_data:
                try:
                    data_fallback = json.loads(raw_data)
                    idno = data_fallback.get('idno')
                except json.JSONDecodeError:
                    pass

    except Exception:
        return jsonify({"success": False, "message": "Server processing error during request retrieval"}), 500

    if not idno:
        return jsonify({"success": False, "message": "No ID provided"}), 400

    student = row_to_dict(get_student_by_idno(idno))
    if not student:
        return jsonify({"success": False, "message": f"Student with ID {idno} not found"}), 404
    
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%I:%M %p").lstrip('0') 
    existing = get_attendance_today(idno, date_str)
    
    if existing:
        existing_dict = dict(existing) if existing else None
        existing_time_24h = existing_dict.get('time_in')
        existing_time_12h = "N/A"
        
        if existing_time_24h:
            try:
                time_to_parse = existing_time_24h.split('.')[0] 
                time_obj = datetime.strptime(time_to_parse, "%H:%M:%S")
                existing_time_12h = time_obj.strftime("%I:%M %p").lstrip('0')
            except ValueError:
                existing_time_12h = existing_time_24h 

        return jsonify({
            "success": True, 
            "student": student,
            "message": f"Attendance already recorded today at {existing_time_12h}"
        })
    
    if record_attendance(idno):
        return jsonify({
            "success": True, 
            "student": student,
            "message": f"Attendance recorded successfully at {time_str}"
        })
    else:
        return jsonify({
            "success": False, 
            "message": "Database error recording attendance"
        }), 500

@app.route("/default-icon")
def default_icon():
    """Serve the default icon from static/icons folder"""
    try:
        icon_path = os.path.join(os.path.dirname(__file__), 'static', 'icons', 'default_icon.webp')
        if os.path.exists(icon_path):
            return send_file(icon_path, mimetype='image/webp')
        else:
            # Fallback: return embedded SVG if file not found
            return send_file(
                io.BytesIO(base64.b64decode('PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyMDAgMjAwIj48cmVjdCBmaWxsPSIjZTVlN2ViIiB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIvPjxjaXJjbGUgY3g9IjEwMCIgY3k9IjcwIiByPSIzMCIgZmlsbD0iIzljYTNhZiIvPjxlbGxpcHNlIGN4PSIxMDAiIGN5PSIxNDAiIHJ4PSI1MCIgcnk9IjM1IiBmaWxsPSIjOWNhM2FmIi8+PC9zdmc+')),
                mimetype='image/svg+xml'
            )
    except Exception as e:
        print(f"Error serving default icon: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/generate-qr/<idno>")
def get_qr_code(idno):
    """
    Generates QR code for a given IDNO with High Error Correction 
    and returns it as a WEBP file INLINE for image tags.
    """
    try:
        img = generate_qr_code_image(idno)
        
        buffer = BytesIO()
        img.save(buffer, format='WEBP')
        buffer.seek(0)
        
        return send_file(
            buffer,
            mimetype='image/webp'
        )

    except NameError:
        print("ERROR: generate_qr_code_image function not found!")
        return jsonify({"success": False, "message": "Server utility not found"}), 500
    except Exception as e:
        print(f"Error generating QR code for {idno}: {e}")
        return jsonify({"success": False, "message": f"Server error: {e}"}), 500

@app.route("/student-profile/<idno>")
def student_profile(idno):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    student = row_to_dict(get_student_by_idno(idno))
    if not student:
        flash("Student not found.", "error")
        return redirect(url_for('student_management'))
    
    filename = student.get('image_filename')
    if filename and os.path.exists(os.path.join(UPLOAD_FOLDER, filename)):
        student['image_url'] = url_for('static', filename=f'images/{filename}')
    else:
        student['image_url'] = DEFAULT_ICON
    
    return render_template("student_profile.html", student=student)

@app.route("/reset-attendance-id")
def reset_attendance_id():
    """Reset attendance table auto-increment counter"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        conn = __import__('dbhelper').connect()
        cur = conn.cursor()
        cur.execute("SELECT MAX(id) FROM attendance")
        max_id = cur.fetchone()[0]
        
        if max_id is None:
            flash("No attendance records found.", "warning")
            return redirect(url_for('view_attendance'))
        cur.execute("DELETE FROM sqlite_sequence WHERE name='attendance'")
        cur.execute("INSERT INTO sqlite_sequence (name, seq) VALUES ('attendance', ?)", (max_id,))
        conn.commit()
        
        flash(f"Attendance ID counter reset successfully! Next ID will be {max_id + 1}.", "success")
        print(f"[RESET] Attendance auto-increment reset to {max_id}")
        
    except Exception as e:
        print(f"Error resetting attendance ID: {e}")
        flash(f"Error resetting ID counter: {e}", "error")
    finally:
        conn.close()
    
    return redirect(url_for('view_attendance'))

@app.route("/test-attendance")
def test_attendance():
    """Test route to check attendance functionality"""
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        test_records = get_attendance_by_date(today)
        test_students = getall('students')
        
        return jsonify({
            "success": True,
            "today": today,
            "attendance_count": len(test_records),
            "students_count": len(test_students)
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

if __name__ == "__main__":
    print(f"Starting Flask from: {os.getcwd()}")
    print(f"Static folder: {app.static_folder}")
    print(f"Static URL path: {app.static_url_path}")
    app.run(debug=True)