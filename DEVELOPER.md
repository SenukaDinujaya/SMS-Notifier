# Developer Documentation

This document provides an in-depth explanation of the SMS-Notifier codebase for developers who want to understand, maintain, or extend the system.

## Table of Contents

1. [System Overview](#system-overview)
2. [Entry Points](#entry-points)
3. [Flask Application Factory](#flask-application-factory)
4. [Database Models](#database-models)
5. [Route Handlers](#route-handlers)
6. [Core SMS Logic](#core-sms-logic)
7. [Thread Management](#thread-management)
8. [Utility Modules](#utility-modules)
9. [Data Flow Diagrams](#data-flow-diagrams)
10. [Key Algorithms](#key-algorithms)
11. [Error Handling](#error-handling)
12. [Extending the System](#extending-the-system)

---

## System Overview

SMS-Notifier is a multi-threaded Flask application that:
1. Provides a web interface for managing VoIP.ms SMS notification accounts
2. Runs background threads that poll VoIP.ms API for missed calls
3. Sends automated SMS/MMS responses to callers

### Technology Stack

- **Backend**: Flask 3.0.3 with SQLAlchemy ORM
- **Database**: SQLite (file-based)
- **Threading**: Python's `threading` module with `ThreadPoolExecutor`
- **External API**: VoIP.ms REST API via `voipms-python` library
- **Production Server**: Gunicorn with Nginx reverse proxy

---

## Entry Points

### Development: `app.py`

```python
# app.py - Main development entry point
```

**Execution Flow:**

1. Calls `create_app()` to initialize Flask application
2. Creates database tables within app context
3. Checks if any users exist; if not, prompts for superuser creation
4. Resets all `Item.running` flags to `False` (clean slate on restart)
5. Starts Flask development server

**Key Code:**

```python
with app.app_context():
    db.create_all()  # Initialize database tables

    if not User.query.first():
        # Interactive superuser creation
        username = input("Enter a username for the superuser: ")
        password = input("Enter a password for the superuser: ")
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

    # Reset all running states on startup
    items = Item.query.all()
    for item in items:
        item.running = False
    db.session.commit()
```

### Production: `wsgi.py`

```python
# wsgi.py - WSGI entry point for Gunicorn
from app import create_app
app = create_app()
```

Simple wrapper that exposes the Flask app to Gunicorn workers.

---

## Flask Application Factory

### Location: `app/__init__.py`

The application uses the factory pattern for flexibility in testing and configuration.

```python
def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)      # Initialize SQLAlchemy
    migrate.init_app(app, db)  # Initialize Flask-Migrate

    from app.routes import main
    app.register_blueprint(main)  # Register route blueprint

    return app
```

**Why Factory Pattern?**
- Allows multiple app instances with different configs
- Enables testing with isolated configurations
- Separates configuration from app creation

---

## Database Models

### Location: `app/models.py`

### User Model

Handles authentication for the web dashboard.

```python
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)  # Hashed with pbkdf2:sha256
```

**Password Hashing:** Uses Werkzeug's `generate_password_hash` with PBKDF2-SHA256.

### Item Model

Represents an SMS notification profile (VoIP.ms account configuration).

```python
class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)      # VoIP.ms email
    password = db.Column(db.String(120), nullable=False)  # VoIP.ms API key
    message = db.Column(db.String(500), nullable=False)   # SMS content
    did = db.Column(db.String(20), nullable=False)        # Phone number
    call_duration = db.Column(db.Integer, nullable=False) # Missed call threshold
    running = db.Column(db.Boolean, default=False)        # Is thread active?
    active = db.Column(db.Boolean, default=True)          # Is account enabled?
    limit_to_one_DID = db.Column(db.Boolean, default=False)  # DID filtering
```

**Field Explanations:**
- `name`: VoIP.ms account email (used for API authentication)
- `password`: VoIP.ms API password (NOT account password)
- `call_duration`: Calls with duration <= this value are considered "missed"
- `running`: Runtime flag indicating if background thread is active
- `limit_to_one_DID`: When `True`, only responds to calls to the specific DID

### Log Model

Stores activity logs from background threads.

```python
class Log(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company = db.Column(db.String(120), nullable=False)   # Account identifier
    timestamp = db.Column(db.DateTime, nullable=False)    # When event occurred
    record = db.Column(db.String(500), nullable=False)    # Log message
```

---

## Route Handlers

### Location: `app/routes.py`

### Authentication Routes

#### `/login` (GET, POST)

```python
@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            session['logged_in'] = True
            return redirect(url_for('main.dashboard'))
        else:
            flash('Invalid username or password')

    return render_template('login.html')
```

**Session Management:**
- Sets `session['logged_in'] = True` on successful login
- Session lifetime: 1800 seconds (30 minutes)
- Uses Flask's secure session cookies

#### `/logout` (GET)

Clears session and redirects to login.

### Dashboard Routes

#### `/` (Dashboard)

```python
@main.route('/')
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('main.login'))

    items = Item.query.all()
    return render_template('dashboard.html', items=items)
```

### CRUD Routes

#### `/create/` (GET, POST)

Creates new Item from form data:
- Extracts: name, password, message, did, call_duration, limit_to_one_DID
- Validates required fields
- Saves to database

#### `/edit/<item_id>` (GET, POST)

Updates existing Item:
- Fetches item by ID or returns 404
- Updates fields from form data
- Commits changes

#### `/delete/<item_id>` (POST)

Deletes Item and its associated logs:

```python
@main.route('/delete/<int:item_id>', methods=['POST'])
def delete_item(item_id):
    item = Item.query.get_or_404(item_id)

    # Delete associated logs first
    Log.query.filter_by(company=item.name).delete()

    db.session.delete(item)
    db.session.commit()

    return redirect(url_for('main.dashboard'))
```

### Thread Control Route

#### `/run_item/<item_id>` (POST)

**Critical route that starts/stops SMS monitoring threads.**

```python
@main.route('/run_item/<int:item_id>', methods=['POST'])
def run_item(item_id):
    item = Item.query.get_or_404(item_id)

    if item.running:
        # Stop the thread
        manager.remove_from_queue(item.id)
        item.running = False
    else:
        # Start the thread
        manager.add_to_queue(item)
        item.running = True

    db.session.commit()
    return redirect(url_for('main.dashboard'))
```

**Manager Integration:**
- `manager.add_to_queue(item)`: Creates SMSSender and starts background thread
- `manager.remove_from_queue(item.id)`: Signals thread to stop

### Logging Routes

#### `/log/` (GET, POST)

**Dual-purpose route:**

**GET**: Display logs for a specific company
```python
if request.method == 'GET':
    company = request.args.get('company')
    logs = Log.query.filter_by(company=company).order_by(Log.timestamp.desc()).all()
    return render_template('logs.html', logs=logs, company=company)
```

**POST**: Receive logs from background threads
```python
if request.method == 'POST':
    data = request.json.get('data')
    company, timestamp, record, token = data

    # Validate token
    if token != current_app.config['LOG_TOKEN']:
        return jsonify({'status': 'error', 'message': 'Invalid token'}), 401

    # Convert epoch to datetime
    dt = datetime.fromtimestamp(timestamp)

    new_log = Log(company=company, timestamp=dt, record=record)
    db.session.add(new_log)
    db.session.commit()

    return jsonify({'status': 'success'})
```

**Security:** Token-based authentication prevents unauthorized log injection.

#### `/export/` (GET, POST)

Exports logs as CSV using pandas:

```python
logs = Log.query.filter_by(company=company).all()
df = pd.DataFrame([(l.company, l.timestamp, l.record) for l in logs],
                  columns=['Company', 'Timestamp', 'Record'])
csv = df.to_csv(index=False)
return Response(csv, mimetype='text/csv',
                headers={'Content-Disposition': f'attachment;filename={company}_logs.csv'})
```

---

## Core SMS Logic

### Location: `app/core/sender.py`

### SMSSender Class

The heart of the application - handles VoIP.ms API interaction and SMS sending.

#### Initialization

```python
class SMSSender:
    def __init__(self, name, password, message, did, call_duration,
                 limit_to_one_did=False, logging=True):
        self.name = name              # VoIP.ms email
        self.password = password      # VoIP.ms API password
        self.message = message        # SMS content
        self.did = did                # Phone number
        self.call_duration = call_duration
        self.limit_to_one_did = limit_to_one_did
        self.logging = logging

        self.history = deque(maxlen=20)  # De-duplication queue
        self.running = True              # Thread control flag
        self.log_sender = LogSender(self.name)  # HTTP log sender

        # Initialize VoIP.ms client
        self.client = voipms.api.Client(self.name, self.password)
        self.sms = ExtendedSMS(self.client)  # SMS/MMS wrapper
```

#### Main Loop: `run()`

```python
def run(self):
    while self.running:
        try:
            self.check_and_send()
        except Exception as e:
            self.log(f"Error in check_and_send: {e}")

        time.sleep(10)  # Poll every 10 seconds
```

#### Core Logic: `check_and_send()`

```python
def check_and_send(self):
    # Step 1: Get today's date range for CDR query
    today = datetime.now(pytz.timezone('America/Toronto'))
    start_date = today.strftime('%Y-%m-%d')
    end_date = start_date

    # Step 2: Fetch Call Detail Records from VoIP.ms
    cdr = self.client.call_detail_records.get(
        date_from=start_date,
        date_to=end_date,
        answered=True,  # Include answered calls
        noanswer=True,  # Include unanswered calls
        busy=True,      # Include busy calls
        failed=True     # Include failed calls
    )

    # Step 3: Convert to DataFrame and filter
    df = pd.DataFrame(cdr['cdr'])

    # Filter for inbound calls only
    inbound_types = ['IN:CAN', 'IN:TOLLFREE']
    df = df[df['destination'].isin(inbound_types)]

    # Filter for "missed" calls (duration <= threshold)
    df = df[df['seconds'].astype(int) <= self.call_duration]

    # Step 4: Process each qualifying call
    for _, row in df.iterrows():
        caller_id = self.normalize_caller_id(row['callerid'])
        call_time = self.parse_call_time(row['date'])

        # Check if call is within last 3 minutes
        if not self.is_recent(call_time):
            continue

        # Check DID filter
        if self.limit_to_one_did and row['destination'] != self.did:
            continue

        # Check de-duplication
        if caller_id in self.history:
            continue

        # Send SMS/MMS
        self.send_message(caller_id)
        self.history.append(caller_id)
```

#### Caller ID Normalization

```python
def normalize_caller_id(self, raw_id):
    """
    Extracts 10-digit phone number from various formats:
    - "John Doe" <15551234567>
    - +15551234567
    - 5551234567
    """
    # Extract digits only
    digits = re.sub(r'\D', '', raw_id)

    # Remove country code if present
    if len(digits) == 11 and digits.startswith('1'):
        digits = digits[1:]

    return digits
```

#### SMS/MMS Decision

```python
def send_message(self, phone_number):
    """
    Sends SMS (< 160 chars) or MMS (>= 160 chars)
    """
    if len(self.message) < 160:
        result = self.sms.send(
            did=self.did,
            dst=phone_number,
            message=self.message
        )
    else:
        result = self.sms.send_mms(
            did=self.did,
            dst=phone_number,
            message=self.message
        )

    self.log(f"Sent message to {phone_number}: {result}")
```

---

## Thread Management

### Location: `app/core/manager/`

The system provides two thread management approaches:

### Active Approach: `manager_2.py`

**Primary manager used in production.**

```python
class Manager:
    def __init__(self):
        self.senders = {}      # {item_id: SMSSender}
        self.lock = Lock()     # Thread safety
        self.queue_thread = None
        self.running = False

    def add_to_queue(self, item):
        """Add new SMS sender to the active pool"""
        with self.lock:
            sender = SMSSender(
                name=item.name,
                password=item.password,
                message=item.message,
                did=item.did,
                call_duration=item.call_duration,
                limit_to_one_did=item.limit_to_one_DID
            )
            self.senders[item.id] = sender

            # Start queue thread if not running
            if not self.running:
                self._start_queue_thread()

    def remove_from_queue(self, item_id):
        """Signal sender to stop and remove from pool"""
        with self.lock:
            if item_id in self.senders:
                self.senders[item_id].running = False
                del self.senders[item_id]

    def _queue_loop(self):
        """Main loop that runs all senders"""
        while self.running:
            with self.lock:
                for sender in list(self.senders.values()):
                    try:
                        sender.check_and_send()
                    except Exception as e:
                        print(f"Sender error: {e}")

            time.sleep(10)
```

**Key Features:**
- Single thread runs all senders sequentially
- Thread-safe operations with `Lock()`
- Auto-restart every 6 hours to prevent memory leaks

### Alternative Approach: `thread_runner.py`

**Per-account threading (alternative architecture).**

```python
class Run:
    def __init__(self, item):
        self.item = item
        self.sender = None
        self.thread = None
        self.running = False

    def start(self):
        self.running = True
        self.thread = Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def _run_loop(self):
        while self.running:
            try:
                if self.sender is None:
                    self.sender = SMSSender(...)
                self.sender.run()
            except Exception as e:
                # Auto-restart on error
                time.sleep(5)
                continue

    def stop(self):
        self.running = False
        if self.sender:
            self.sender.running = False
```

**When to use:**
- Need true parallel execution
- Different accounts have vastly different polling frequencies
- Isolation between accounts is critical

---

## Utility Modules

### Location: `app/core/utils/`

### LogSender (`log.py`)

Sends logs from background threads to the Flask `/log/` endpoint.

```python
class LogSender:
    def __init__(self, company):
        self.company = company
        self.endpoint = 'http://127.0.0.1:8000/log/'

    def send(self, message):
        """Send log entry to Flask endpoint"""
        timestamp = time.time()
        payload = {
            'data': [self.company, timestamp, message, LOG_TOKEN]
        }

        try:
            response = requests.post(self.endpoint, json=payload, timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            return False
```

**Why HTTP for logging?**
- Background threads run in separate context from Flask
- Direct database access from threads can cause SQLAlchemy issues
- HTTP provides clean separation and token-based security

### ExtendedSMS (`extended_voipms.py`)

Extends `voipms-python` to support MMS.

```python
class ExtendedSMS:
    def __init__(self, client):
        self.client = client
        self.sms = client.sms

    def send(self, did, dst, message):
        """Standard SMS send"""
        return self.sms.send(did=did, dst=dst, message=message)

    def send_mms(self, did, dst, message):
        """MMS send for messages >= 160 chars"""
        # VoIP.ms MMS endpoint
        return self.client._make_request('sendMMS', {
            'did': did,
            'dst': dst,
            'message': message
        })
```

### Timezone Utilities

#### EpochToDateTime (`epoch_to_dt.py`)

```python
def epoch_to_datetime(epoch_timestamp):
    """Convert Unix timestamp to Toronto timezone datetime"""
    tz = pytz.timezone('America/Toronto')
    return datetime.fromtimestamp(epoch_timestamp, tz)
```

#### DayLightSaving (`dls.py`)

```python
def is_dst():
    """Check if Toronto is currently in Daylight Saving Time"""
    tz = pytz.timezone('America/Toronto')
    now = datetime.now(tz)
    return bool(now.dst())
```

---

## Data Flow Diagrams

### Request Flow: Starting a Monitor

```
User clicks "Run" on dashboard
         │
         ▼
POST /run_item/<item_id>
         │
         ▼
┌─────────────────────────────┐
│  Route Handler              │
│  1. Fetch Item from DB      │
│  2. Check current state     │
│  3. Call manager.add()      │
│  4. Set item.running=True   │
│  5. Commit to DB            │
└─────────────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│  Manager.add_to_queue()     │
│  1. Create SMSSender        │
│  2. Add to senders dict     │
│  3. Start queue thread      │
└─────────────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│  Queue Thread Loop          │
│  (Every 10 seconds)         │
│  1. Lock senders dict       │
│  2. For each sender:        │
│     - check_and_send()      │
│  3. Release lock            │
│  4. Sleep 10 seconds        │
└─────────────────────────────┘
```

### SMS Detection Flow

```
SMSSender.check_and_send()
         │
         ▼
┌─────────────────────────────┐
│  Fetch CDR from VoIP.ms     │
│  GET /api/v1/getCDR         │
│  - date_from: today         │
│  - date_to: today           │
└─────────────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│  Filter DataFrame           │
│  1. Inbound only            │
│  2. Duration <= threshold   │
│  3. Recent (< 3 min ago)    │
│  4. Not in history          │
│  5. DID match (if enabled)  │
└─────────────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│  For each qualifying call   │
│  1. Normalize caller ID     │
│  2. Send SMS or MMS         │
│  3. Add to history deque    │
│  4. Log the action          │
└─────────────────────────────┘
```

### Logging Flow

```
SMSSender logs an event
         │
         ▼
LogSender.send(message)
         │
         ▼
POST /log/ with JSON:
{
  "data": [company, timestamp, message, token]
}
         │
         ▼
┌─────────────────────────────┐
│  /log/ Route Handler        │
│  1. Validate LOG_TOKEN      │
│  2. Convert timestamp       │
│  3. Create Log object       │
│  4. Commit to database      │
└─────────────────────────────┘
```

---

## Key Algorithms

### De-duplication Algorithm

**Problem:** VoIP.ms CDR may return the same call multiple times. We need to avoid sending duplicate SMS.

**Solution:** Use a bounded deque (maxlen=20) as a rolling history.

```python
self.history = deque(maxlen=20)

# Before sending
if caller_id in self.history:
    return  # Already sent

# After sending
self.history.append(caller_id)
```

**Trade-offs:**
- 20 items is a balance between memory and coverage
- Older callers calling back will receive SMS again
- Consider increasing for high-volume scenarios

### Recent Call Detection

**Problem:** VoIP.ms CDR has ~2-minute lag. We need to detect calls quickly without duplicates.

**Solution:** Check if call occurred within the last 3 minutes.

```python
def is_recent(self, call_time):
    now = datetime.now(pytz.timezone('America/Toronto'))
    delta = now - call_time
    return delta.total_seconds() <= 180  # 3 minutes
```

**Why 3 minutes?**
- VoIP.ms CDR lag: ~2 minutes
- Polling interval: 10 seconds
- Buffer: 1 minute for safety

### SMS vs MMS Decision

**Simple length-based decision:**

```python
if len(message) < 160:
    send_sms()
else:
    send_mms()
```

**Note:** SMS has 160 character limit. MMS allows longer messages but may have higher cost.

---

## Error Handling

### Thread-Level Recovery

```python
def _run_loop(self):
    while self.running:
        try:
            self.sender.check_and_send()
        except Exception as e:
            self.log_sender.send(f"Error: {e}")
            time.sleep(5)  # Back-off before retry
            continue
```

**Strategy:**
- Catch all exceptions to prevent thread death
- Log errors for debugging
- Back-off 5 seconds to prevent rapid retry loops
- Continue running to maintain service

### API Error Handling

```python
try:
    cdr = self.client.call_detail_records.get(...)
except voipms.api.exceptions.VoIPMSException as e:
    self.log(f"VoIP.ms API error: {e}")
    return  # Skip this iteration
except requests.RequestException as e:
    self.log(f"Network error: {e}")
    return
```

---

## Extending the System

### Adding New Message Variables

To support dynamic message content (e.g., caller name):

1. Modify `SMSSender.send_message()`:

```python
def send_message(self, phone_number, call_data):
    message = self.message
    message = message.replace('{caller}', call_data.get('callerid', ''))
    message = message.replace('{time}', call_data.get('date', ''))
    # ... send message
```

2. Update message field in dashboard to explain variables.

### Adding New Notification Channels

To add email notifications:

1. Create `app/core/email_sender.py`
2. Add email fields to `Item` model
3. Call email sender alongside SMS in `check_and_send()`

### Adding Webhooks

For external integrations:

1. Add webhook URL field to `Item` model
2. POST call data to webhook on missed call detection
3. Handle webhook failures gracefully

### Scaling Considerations

For high-volume deployments:

1. **Database:** Migrate from SQLite to PostgreSQL
2. **Threading:** Use Celery for distributed task processing
3. **Caching:** Add Redis for history de-duplication across workers
4. **Monitoring:** Add Prometheus metrics and alerting

---

## Testing

### Manual Testing Checklist

1. **Account Creation:** Create account with valid VoIP.ms credentials
2. **Start Monitoring:** Click "Run" and verify thread starts
3. **Call Detection:** Make test call, let it ring, verify SMS received
4. **De-duplication:** Call again immediately, verify no duplicate SMS
5. **Stop Monitoring:** Click "Run" again, verify thread stops
6. **Logs:** Check logs page shows activity
7. **Export:** Export logs as CSV, verify format

### Unit Testing (Future)

```python
# Example test structure
def test_normalize_caller_id():
    sender = SMSSender(...)
    assert sender.normalize_caller_id('"John" <15551234567>') == '5551234567'
    assert sender.normalize_caller_id('+15551234567') == '5551234567'
    assert sender.normalize_caller_id('5551234567') == '5551234567'
```

---

## Debugging Tips

1. **Enable Debug Mode:** Set `DEBUG = True` in config.py
2. **Check Thread Status:** Add print statements in `_queue_loop()`
3. **VoIP.ms API Testing:** Use VoIP.ms web portal to verify CDR data
4. **Log Inspection:** Check `/log/` page for error messages
5. **Database Inspection:** Use SQLite browser to inspect `app.db`

---

## Code Style Guidelines

- Follow PEP 8 for Python code
- Use type hints for function signatures
- Document complex logic with inline comments
- Keep functions focused and under 50 lines
- Use meaningful variable names
- Handle all exceptions explicitly
