from flask import Flask, render_template, request, redirect, url_for, session, Blueprint
from werkzeug.security import check_password_hash, generate_password_hash
from app.core.manager.thread_manager import Manager
from app.models import Item, User
from . import db
bp = Blueprint('main', __name__)

thread_manager = Manager()

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
        return render_template('dashboard.html', user=user,items = items)
    else:
        return redirect(url_for('main.login'))
    
@bp.route('/create/', methods=['POST','GET'])
def create_item():
    if request.method == 'POST':
        name = request.form['name']
        password = request.form['password']
        message = request.form['message']
        did = request.form['did']
        call_duration = request.form['call_duration']
        timezone_diff = -1

        new_item = Item(
            name=name,
            password=password,
            message=message,
            did=did,
            call_duration=call_duration,
            timezone_diff=timezone_diff,
            running=False,
            active=False
        )

        db.session.add(new_item)
        db.session.commit()
        
        return redirect(url_for('main.dashboard'))
    else:
        return render_template('create_account.html')
    

@bp.route('/edit/<string:item_id>', methods=['GET', 'POST'])
def edit_item(item_id):
    item = Item.query.get_or_404(item_id)
    if request.method == 'POST':
        item.name = request.form['new_item_name']
        item.password = request.form['new_password']
        item.message = request.form['new_message']
        item.did = request.form['new_did']
        item.call_duration = request.form['new_call_duration']
        item.timezone_diff = -1
        item.active = False
        item.running = False
        thread_manager.remove_thread(item_id)
        db.session.commit()
        return redirect(url_for('main.dashboard'))

    return render_template('edit.html', item=item)


@bp.route('/run_item/<item_id>', methods=['POST'])
def run_item(item_id):
    # Define the function to be executed in a separate thread
    item = Item.query.get_or_404(item_id)
    
    if request.method == 'POST' and not item.active:
        item.active = True
        item.running = True
        thread_manager.add_thread(item_id,item)

    else:
        item.active = False
        item.running = False
        thread_manager.remove_thread(item_id)

    db.session.commit()
    return redirect(url_for('main.dashboard'))

@bp.route('/delete/<string:item_id>', methods=['POST'])
def delete_item(item_id):
    item = Item.query.get_or_404(item_id)
    thread_manager.remove_thread(item_id)
    db.session.delete(item)
    db.session.commit()
    return redirect(url_for('main.dashboard'))