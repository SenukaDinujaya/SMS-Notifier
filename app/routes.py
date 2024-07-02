from flask import Flask, render_template, request, redirect, url_for, session, Blueprint, jsonify, Response
from werkzeug.security import check_password_hash, generate_password_hash
from app.core.manager.manager_2 import Manager
from app.core.utils.dls import DayLightSaving
from app.core.utils.epoch_to_dt import EpochToDateTime
from app.models import Item, User,Log
from app.config import Config
from functools import wraps
from . import db
bp = Blueprint('main', __name__)

thread_manager = Manager()
dls = DayLightSaving()
epoch_to_datetime = EpochToDateTime()


request_queue = []

def queue_database_modification(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Add incoming request to the queue
        request_queue.append((func, args, kwargs))
        # Process all requests in the queue one at a time
        for queued_func, queued_args, queued_kwargs in request_queue:
            result = queued_func(*queued_args, **queued_kwargs)
        # Clear the queue after processing
        request_queue.clear()
        return result  # Return the result of the wrapped function
    return wrapper


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['user_name']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            return redirect(url_for('main.dashboard'))
    
    return render_template('login.html')


@bp.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('main.login'))


@bp.route('/')
def dashboard():
    if 'user_id' in session:
        user_id = session['user_id']
        user = User.query.get(user_id)
        items = Item.query.all()
        return render_template('dashboard.html', user=user,items = items, dls= dls.is_dst_in_toronto())
    else:
        return redirect(url_for('main.login'))
    
@bp.route('/create/', methods=['POST','GET'])
@queue_database_modification
def create_item():
    if 'user_id' in session:
        if request.method == 'POST':
            name = request.form['name']
            password = request.form['password']
            message = request.form['message']
            did = request.form['did']
            call_duration = request.form['call_duration']
            limit_to_one_DID = bool(request.form['limit_to_one_DID'])

            new_item = Item(
                name=name,
                password=password,
                message=message,
                did=did,
                call_duration=call_duration,
                running=False,
                active=False,
                limit_to_one_DID=limit_to_one_DID,
            )

            db.session.add(new_item)
            db.session.commit()
            
            return redirect(url_for('main.dashboard'))
        else:
            return render_template('create_account.html')
    else:    
        return redirect(url_for('main.login'))
    

@bp.route('/edit/<string:item_id>', methods=['GET', 'POST'])
@queue_database_modification
def edit_item(item_id):
    if 'user_id' in session:
        item = Item.query.get_or_404(item_id)
        thread_manager.stop(item)
        if request.method == 'POST':
            item.name = request.form['new_item_name']
            item.password = request.form['new_password']
            item.message = request.form['new_message']
            item.did = request.form['new_did']
            item.call_duration = request.form['new_call_duration']
            item.limit_to_one_DID = bool(request.form.get('limit_to_one_DID'))
            item.active = False
            item.running = False
            db.session.commit()
            return redirect(url_for('main.dashboard'))

        return render_template('edit.html', item=item)
    else:
        return redirect(url_for('main.login'))


@bp.route('/run_item/<item_id>', methods=['POST'])
@queue_database_modification
def run_item(item_id):
    if 'user_id' not in session:
        return redirect(url_for('main.login'))

    item = Item.query.get_or_404(item_id)

    if request.method == 'POST' and not item.active:
        item.active = True
        item.running = True
        thread_manager.add_to_queue(item)
    else:
        item.active = False
        item.running = False
        thread_manager.stop(item)


    db.session.commit()
    return redirect(url_for('main.dashboard'))

    
@bp.route('/delete/<string:item_id>', methods=['POST'])
@queue_database_modification
def delete_item(item_id):
    if 'user_id' in session:
        item = Item.query.get_or_404(item_id)
        thread_manager.stop(item)
        db.session.delete(item)
        db.session.commit()
        return redirect(url_for('main.dashboard'))
    else:
        return redirect(url_for('main.login'))

@bp.route('/log/', methods=['POST','GET'])
@queue_database_modification
def log_item():
    if request.method == 'POST':
        data = request.get_json().get('data')
        if Config.LOG_TOKEN == data[3]:
            new_log = Log(
                company = data[0],
                timestamp = epoch_to_datetime.epoch_to_datetime(data[1]),
                record = data[2]
            )

            db.session.add(new_log)
            db.session.commit()
            return jsonify({'message': 'Log added successfully'}), 200
        else:    
            return redirect(url_for('main.login'))
    else:
        if 'user_id' in session:
            log_items = Log.query.order_by(Log.id.desc()).all()

            return render_template('logs.html', log_items = log_items)
        else:    
            return redirect(url_for('main.login'))
        
def export(log_items):
    # Create a CSV response
    def generate():
        # Write header
        yield 'Timestamp,Account,Log\n'
        for log in log_items:
            # Write log item rows
            yield f'{log.timestamp},{log.company},{log.record}\n'

    # Create a response object and specify the content type and headers
    response = Response(generate(), mimetype='text/csv')
    response.headers.set("Content-Disposition", "attachment", filename="logs.csv")
    return response

@bp.route('/export/', methods=['POST','GET'])
@queue_database_modification
def export_items():
    if request.method == 'POST':
        if 'user_id' in session:
            log_items = Log.query.order_by(Log.id.desc()).all()

            return export(log_items = log_items)
        else:    
            return redirect(url_for('main.login'))
        