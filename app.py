from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
load_dotenv()
from datetime import datetime, timedelta
import os, json, random, string, io, base64, smtplib, threading, math, time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
app.config['SECRET_KEY'] = 'bhumismarthagri2024secretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///smart_agriculture.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('static/reports', exist_ok=True)
os.makedirs('models', exist_ok=True)

MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
OPENWEATHER_KEY = os.environ.get('OPENWEATHER_KEY')
DATAGOV_KEY = os.environ.get('DATAGOV_KEY')


MANDI_PRICES = {
    'Tomato':(18.0,'high'), 'Onion':(22.0,'high'), 'Potato':(15.0,'high'),
    'Chilli':(85.0,'high'), 'Maize':(22.0,'medium'), 'Paddy':(22.0,'high'),
    'Cotton':(62.0,'high'), 'Soybean':(48.0,'high'), 'Groundnut':(58.0,'high'),
    'Wheat':(24.0,'high'), 'Rice':(38.0,'high'), 'Turmeric':(120.0,'high'),
    'Redgram':(95.0,'high'), 'Chickpea':(65.0,'medium'), 'Sunflower':(52.0,'medium'),
    'Mustard':(58.0,'high'), 'Moong':(75.0,'high'), 'Garlic':(90.0,'high'),
    'Banana':(28.0,'high'), 'Mango':(55.0,'high'), 'Bajra':(20.0,'medium'),
    'Jowar':(20.0,'medium'), 'Ragi':(28.0,'medium'), 'Sugarcane':(4.0,'high'),
    'Coconut':(22.0,'medium'), 'Watermelon':(12.0,'medium'), 'Brinjal':(15.0,'medium'),
    'Ginger':(45.0,'medium'), 'Cumin':(180.0,'high'), 'Sesame':(110.0,'medium'),
    'Castor':(58.0,'medium'), 'Horsegram':(60.0,'medium'), 'Coriander':(85.0,'medium'),
    'Grapes':(65.0,'high'), 'Tobacco':(95.0,'medium'), 'Cashew':(800.0,'high'),
    'Vegetables':(20.0,'high'), 'Flowers':(45.0,'high'), 'Safflower':(55.0,'medium'),
    'Tur':(70.0,'high'), 'Leafy Greens':(15.0,'high'), 'Leafy Vegetables':(15.0,'high'),
    'Onion':(22.0,'high'), 'Jasmine':(200.0,'high'), 'Rose':(80.0,'high'),
    'Marigold':(20.0,'high'), 'Orange':(40.0,'medium'), 'Guava':(30.0,'medium'),
    'Papaya':(22.0,'medium'), 'Litchi':(80.0,'high'), 'Jute':(42.0,'medium'),'Cucumber'    : (12.0,  'medium'), 'Bitter Gourd': (18.0,  'medium'),'Okra'        : (20.0,  'high'),
    'Beans'       : (25.0,  'medium'),'Carrot'      : (25.0,  'medium'), 'Brinjal'     : (15.0,  'medium'),
    'Tomato'      : (18.0,  'high'),'Onion'       : (22.0,  'high'),'Chilli'      : (85.0,  'high'),
    'Marigold'    : (20.0,  'high'),'Banana'      : (28.0,  'high'),
}

def get_live_crop_price(crop_name, state, district):
    import requests

    # These crops are NOT traded in mandis — never show 🔴
    NON_MANDI_CROPS = {
        'Vegetables','Flowers','Leafy Greens','Leafy Vegetables',
        'Marigold','Rose','Jasmine','Chrysanthemum','Tuberose',
        'Gladiolus','Aloe Vera','Fern','Bamboo Plant','Snake Plant',
        'Peace Lily','Rubber Plant','Okra','Bitter Gourd','Cucumber',
        'Beans','Carrot','Broccoli','Lettuce','Indoor Plants',
    }
    if crop_name in NON_MANDI_CROPS:
        return None, None

    CROP_MAP = {
        'Tomato':'Tomato','Onion':'Onion','Potato':'Potato',
        'Chilli':'Chilli(Dry)','Maize':'Maize',
        'Paddy':'Paddy(Common)','Cotton':'Cotton',
        'Soybean':'Soyabean','Groundnut':'Groundnut',
        'Wheat':'Wheat','Rice':'Rice','Turmeric':'Turmeric',
        'Redgram':'Arhar (Tur/Red Gram)(Whole)',
        'Chickpea':'Bengal Gram(Gram)(Whole)',
        'Sunflower':'Sunflower','Mustard':'Mustard',
        'Moong':'Moong (Whole)','Garlic':'Garlic',
        'Banana':'Banana','Mango':'Mango',
        'Jowar':'Jowar(Sorghum)',
        'Bajra':'Bajra(Pearl Millet/Cumbu)',
        'Ragi':'Ragi (Finger Millet)',
        'Castor':'Castor Seed',
        'Sesame':'Sesamum(Sesame/Til)',
        'Cumin':'Cummin Seed(Jeera)',
        'Coriander':'Coriander(Leaves)',
        'Ginger':'Ginger(Dry)','Horsegram':'Horse Gram',
        'Coconut':'Coconut','Grapes':'Grapes',
        'Watermelon':'Water Melon','Brinjal':'Brinjal',
        'Sugarcane':'Sugarcane','Tobacco':'Tobacco',
        'Tur':'Arhar (Tur/Red Gram)(Whole)',
    }

    agmark_name = CROP_MAP.get(crop_name)
    if not agmark_name:
        return None, None  # ← No 🔴 for unknown crops

    try:
        url = (
            "https://api.data.gov.in/resource/"
            "9ef84268-d588-465a-a308-a864a43d0070"
            f"?api-key={DATAGOV_KEY}&format=json&limit=5"
            f"&filters[commodity]={agmark_name}"
        )
        resp    = requests.get(url, timeout=3)
        data    = resp.json()
        records = data.get('records', [])
        if records:
            modal = float(records[0].get('Modal_Price', 0))
            if modal > 0:
                price_per_kg = round(modal / 100, 2)
                demand = 'high' if modal > 2000 else 'medium'
                print(f"✅ LIVE {crop_name} {state}: ₹{price_per_kg}/kg")
                return price_per_kg, demand
    except Exception as e:
        print(f"⚠️ API error {crop_name}: {e}")

    
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ─────────────────────────────────────────────
# MODELS
# ─────────────────────────────────────────────
class Farmer(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(15), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    state = db.Column(db.String(50))
    district = db.Column(db.String(50))
    language = db.Column(db.String(10), default='en')
    profile_photo = db.Column(db.String(200), default='default.png')
    reset_token = db.Column(db.String(100))
    reset_expiry = db.Column(db.DateTime)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class SoilAnalysis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    farmer_id = db.Column(db.Integer, db.ForeignKey('farmer.id'))
    soil_type = db.Column(db.String(50))
    state = db.Column(db.String(50))
    district = db.Column(db.String(50))
    season = db.Column(db.String(20))
    image_path = db.Column(db.String(200))
    health_score = db.Column(db.Float)
    features = db.Column(db.Text)
    result = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class DiseaseDetection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    farmer_id = db.Column(db.Integer, db.ForeignKey('farmer.id'))
    image_path = db.Column(db.String(200))
    disease_name = db.Column(db.String(100))
    confidence = db.Column(db.Float)
    cause = db.Column(db.String(200))
    treatment = db.Column(db.Text)
    organic_option = db.Column(db.Text)
    prevention = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Order(db.Model):
    __tablename__ = 'orders'
    id          = db.Column(db.Integer, primary_key=True)
    farmer_id   = db.Column(db.Integer, db.ForeignKey('farmer.id'), nullable=False)
    order_id    = db.Column(db.String(20), unique=True)
    items       = db.Column(db.Text)
    total       = db.Column(db.Float)
    payment     = db.Column(db.String(20))
    status      = db.Column(db.String(20), default='Confirmed')
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

class GovernmentScheme(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    name_hi = db.Column(db.String(200))
    name_te = db.Column(db.String(200))
    scheme_type = db.Column(db.String(20))
    category = db.Column(db.String(50))
    state = db.Column(db.String(50), default='All')
    description = db.Column(db.Text)
    description_hi = db.Column(db.Text)
    description_te = db.Column(db.Text)
    benefit = db.Column(db.String(300))
    eligibility = db.Column(db.Text)
    how_to_apply = db.Column(db.Text)
    documents = db.Column(db.Text)
    official_link = db.Column(db.String(300))
    last_date = db.Column(db.String(50))
    is_active = db.Column(db.Boolean, default=True)

class ContactMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    farmer_id = db.Column(db.Integer, db.ForeignKey('farmer.id'))
    name = db.Column(db.String(100))
    email = db.Column(db.String(120))
    subject = db.Column(db.String(200))
    message = db.Column(db.Text)
    reply = db.Column(db.Text)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class MarketPrice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    crop_name = db.Column(db.String(100))
    price_per_kg = db.Column(db.Float)
    demand = db.Column(db.String(20))
    state = db.Column(db.String(50))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return Farmer.query.get(int(user_id))

# ─────────────────────────────────────────────
# TRANSLATIONS
# ─────────────────────────────────────────────
TRANSLATIONS = {
    'en': {
        'home':'Home','crop_ideas':'Crop Ideas','disease_prediction':'Disease Prediction',
        'schemes':'Government Schemes','help':'Help & Contact','profile':'Profile',
        'logout':'Logout','welcome':'Welcome','login':'Login','register':'Register',
        'select_language':'Select Your Language','continue':'Continue',
        'upload_soil':'Upload Soil Image','select_state':'Select State',
        'select_district':'Select District','select_season':'Select Season',
        'analyze':'Analyze Soil','soil_type':'Soil Type','soil_features':'Soil Features',
        'recommended_crops':'Recommended Crops','vegetables':'Vegetables','fruits':'Fruits',
        'flowers':'Flowers','indoor_plants':'Indoor Plants','market_demand':'Market Demand',
        'high':'High','medium':'Medium','low':'Low','upload_leaf':'Upload Crop/Leaf Image',
        'detect_disease':'Detect Disease','disease_name':'Disease Name',
        'treatment':'Suggested Treatment','prevention':'Prevention Tips',
        'all_schemes':'All Schemes','central_govt':'Central Government',
        'state_govt':'State Government','benefits':'Benefits','eligibility':'Eligibility',
        'apply_now':'Apply Now','view_details':'View Details','search_schemes':'Search Schemes...',
        'contact_us':'Contact Us','your_name':'Your Name','your_email':'Your Email',
        'your_message':'Your Message','send_message':'Send Message',
        'faq':'Frequently Asked Questions','submit':'Submit',
        'kharif':'Kharif (June-Oct)','rabi':'Rabi (Nov-Mar)','zaid':'Zaid (Apr-Jun)',
        'health_score':'Soil Health Score','confidence':'Confidence','cause':'Cause',
        'organic_option':'Organic Option','dashboard':'Dashboard',
        'download_report':'Download PDF Report','market':'🛒 AgriMart','market_prices':'Live Market Prices',
        'forgot_password':'Forgot Password?','reset_password':'Reset Password',
        'change_password':'Change Password','upload_photo':'Upload Profile Photo',
        'notifications':'Notifications','unread':'Unread Messages',
        'image_error':'Please upload a valid image file (JPG, PNG, GIF)',
        'subject':'Subject','admin_panel':'Admin Panel','district_crops_title': 'District-Recommended Crops',
        'trust_note': 'These crops are proven winners in your district based on historical farming data.',   
        # Crop Ideas - new features
        'weather_intel':'Weather Intelligence',
        'temperature':'Temperature','rainfall':'Rainfall',
        'humidity':'Humidity','drought_risk':'Drought Risk',
        'drought_alert':'⚠️ High Drought Risk! Low rainfall predicted. Drought-resistant crops prioritized.',
        'top_recommendation':'⭐ TOP RECOMMENDATION',
        'based_on_ai':'Based on soil + weather + profit analysis',
        'est_profit':'Est. Profit/acre','risk_score':'Risk Score','water_need':'Water Need',
        'recommended_crops_for':'Recommended Crops for',
        'compare_crops':'📊 Compare All Crops',
        'compare_table':'📊 Crop Comparison Table',
        'investment':'Investment/acre','revenue':'Revenue/acre',
        'profit_acre':'Profit/acre','season_ok':'Season OK',
        'in_season':'✅ In Season','off_season':'⚠️ Off-season','drought_ok':'Drought OK',
        'ai_risk_score':'🧠 AI Risk Score','click_calendar':'📅 Click for farming calendar',
        'farming_calendar':'📅 Farming Calendar','download_pdf_cal':'📥 Download PDF Calendar',
        'soil_health_plan':'🧪 Soil Health Improvement Plan',
        'req_fertilizers':'⚗️ Required Fertilizers','organic_compost':'🌿 Organic Compost',
        'crop_rotation':'🔄 Crop Rotation Plan','green_manure':'🌿 Green Manure',
        'alt_crops':'🌾 Alternative Crop Suggestions',
        'alt_crops_note':'If your primary crop fails, these have lower risk and proven success.',
        'success_story':'📍 Nearby Farmer Success Story',
        'farmers_succeeded':'% farmers succeeded','avg_profit':'💰 Average profit',
        'expert_consult':'🧑‍🌾 Expert Consultation',
        'ai_chatbot':'AI Chatbot','ask_ai_btn':'💬 Ask AI',
        'kisan_helpline':'Kisan Helpline','submit_query':'Submit Query',
        'submit_query_btn':'📝 Submit Query','voice_guidance':'🔊 Voice Guidance',
        'enter_farm_details':'📋 Enter Farm Details',
        'farm_size':'📐 Farm Size (acres)','soil_image':'📸 Soil Image',
        'analyze_btn':'🔍 Analyze & Get Recommendations',
        'health_score_lbl':'Health Score',
        # Disease - new features
        'upload_leaf_img':'📸 Upload Leaf Image',
        'click_upload':'Click to upload leaf photo',
        'detect_btn':'🔍 Detect Disease',
        'recent_detections':'🕐 Recent Detections',
        'ai_confidence':'🎯 AI Confidence Score',
        'severity_lbl':'Severity','est_treatment_cost':'Estimated Treatment Cost',
        'also_affects':'⚠️ Also Affects These Crops',
        'chemical_treatment':'💊 Chemical Treatment',
        'organic_option_tab':'🌿 Organic Option',
        'prevention_tab':'🛡️ Prevention',
        'spray_schedule':'🗓️ Day-by-Day Spray Schedule',
        'share_whatsapp':'Share on WhatsApp',
        'download_pdf_report':'📥 Download PDF Report',
        'share_actions':'📤 Share & Actions',
        'upload_prompt':'Upload a leaf image to detect disease',
        'day_lbl':'Day','action_lbl':'Action','product_lbl':'Product','time_lbl':'Time',
    },
    'hi': {
        'home':'होम','crop_ideas':'फसल विचार','disease_prediction':'रोग पहचान',
        'schemes':'सरकारी योजनाएं','help':'सहायता','profile':'प्रोफाइल',
        'logout':'लॉगआउट','welcome':'स्वागत','login':'लॉगिन','register':'पंजीकरण',
        'select_language':'भाषा चुनें','continue':'जारी रखें',
        'upload_soil':'मिट्टी की तस्वीर अपलोड करें','select_state':'राज्य चुनें',
        'select_district':'जिला चुनें','select_season':'मौसम चुनें',
        'analyze':'मिट्टी विश्लेषण करें','soil_type':'मिट्टी का प्रकार',
        'soil_features':'मिट्टी की विशेषताएं','recommended_crops':'अनुशंसित फसलें',
        'vegetables':'सब्जियां','fruits':'फल','flowers':'फूल','indoor_plants':'इनडोर पौधे',
        'market_demand':'बाजार मांग','high':'उच्च','medium':'मध्यम','low':'कम',
        'upload_leaf':'पत्ती की तस्वीर अपलोड करें','detect_disease':'रोग पहचानें',
        'disease_name':'रोग का नाम','treatment':'उपचार','prevention':'रोकथाम',
        'all_schemes':'सभी योजनाएं','central_govt':'केंद्र सरकार','state_govt':'राज्य सरकार',
        'benefits':'लाभ','eligibility':'पात्रता','apply_now':'आवेदन करें',
        'view_details':'विवरण देखें','search_schemes':'योजनाएं खोजें...',
        'contact_us':'संपर्क करें','your_name':'आपका नाम','your_email':'आपका ईमेल',
        'your_message':'आपका संदेश','send_message':'संदेश भेजें',
        'faq':'अक्सर पूछे जाने वाले प्रश्न','submit':'जमा करें',
        'kharif':'खरीफ (जून-अक्टूबर)','rabi':'रबी (नवंबर-मार्च)','zaid':'जायद (अप्रैल-जून)',
        'health_score':'मिट्टी स्वास्थ्य स्कोर','confidence':'विश्वास','cause':'कारण',
        'organic_option':'जैविक विकल्प','dashboard':'डैशबोर्ड',
        'download_report':'PDF रिपोर्ट डाउनलोड करें','market':'🛒 अग्रिमार्ट','market_prices':'बाजार भाव',
        'forgot_password':'पासवर्ड भूल गए?','reset_password':'पासवर्ड रीसेट करें',
        'change_password':'पासवर्ड बदलें','upload_photo':'फोटो अपलोड करें',
        'notifications':'सूचनाएं','unread':'अपठित संदेश',
        'image_error':'कृपया एक वैध छवि फ़ाइल अपलोड करें (JPG, PNG, GIF)',
        'subject':'विषय','admin_panel':'एडमिन पैनल','district_crops_title': 'जिले की अनुशंसित फसलें',
        'trust_note': 'ये फसलें आपके जिले में ऐतिहासिक डेटा के आधार पर सिद्ध सफल फसलें हैं।',
        # Crop Ideas - new features
        'weather_intel':'मौसम जानकारी',
        'temperature':'तापमान','rainfall':'वर्षा',
        'humidity':'आर्द्रता','drought_risk':'सूखा जोखिम',
        'drought_alert':'⚠️ उच्च सूखा जोखिम! कम वर्षा की संभावना। सूखा-प्रतिरोधी फसलें प्राथमिकता में।',
        'top_recommendation':'⭐ शीर्ष सिफारिश',
        'based_on_ai':'मिट्टी + मौसम + लाभ विश्लेषण पर आधारित',
        'est_profit':'अनुमानित लाभ/एकड़','risk_score':'जोखिम स्कोर','water_need':'पानी की जरूरत',
        'recommended_crops_for':'अनुशंसित फसलें',
        'compare_crops':'📊 सभी फसलें तुलना करें',
        'compare_table':'📊 फसल तुलना तालिका',
        'investment':'निवेश/एकड़','revenue':'राजस्व/एकड़',
        'profit_acre':'लाभ/एकड़','season_ok':'मौसम उचित',
        'in_season':'✅ मौसम में','off_season':'⚠️ मौसम के बाहर','drought_ok':'सूखा ठीक',
        'ai_risk_score':'🧠 AI जोखिम स्कोर','click_calendar':'📅 कैलेंडर के लिए क्लिक करें',
        'farming_calendar':'📅 कृषि कैलेंडर','download_pdf_cal':'📥 PDF कैलेंडर डाउनलोड',
        'soil_health_plan':'🧪 मिट्टी स्वास्थ्य सुधार योजना',
        'req_fertilizers':'⚗️ आवश्यक उर्वरक','organic_compost':'🌿 जैविक खाद',
        'crop_rotation':'🔄 फसल चक्र योजना','green_manure':'🌿 हरी खाद',
        'alt_crops':'🌾 वैकल्पिक फसल सुझाव',
        'alt_crops_note':'यदि मुख्य फसल विफल हो, ये फसलें कम जोखिम वाली हैं।',
        'success_story':'📍 पास के किसान की सफलता की कहानी',
        'farmers_succeeded':'% किसान सफल रहे','avg_profit':'💰 औसत लाभ',
        'expert_consult':'🧑‍🌾 विशेषज्ञ परामर्श',
        'ai_chatbot':'AI चैटबॉट','ask_ai_btn':'💬 AI से पूछें',
        'kisan_helpline':'किसान हेल्पलाइन','submit_query':'प्रश्न भेजें',
        'submit_query_btn':'📝 प्रश्न भेजें','voice_guidance':'🔊 आवाज मार्गदर्शन',
        'enter_farm_details':'📋 खेत की जानकारी दर्ज करें',
        'farm_size':'📐 खेत का आकार (एकड़)','soil_image':'📸 मिट्टी की तस्वीर',
        'analyze_btn':'🔍 विश्लेषण करें और सिफारिशें पाएं',
        'health_score_lbl':'स्वास्थ्य स्कोर',
        # Disease - new features
        'upload_leaf_img':'📸 पत्ती की तस्वीर अपलोड करें',
        'click_upload':'पत्ती की तस्वीर के लिए क्लिक करें',
        'detect_btn':'🔍 रोग पहचानें',
        'recent_detections':'🕐 हाल की पहचान',
        'ai_confidence':'🎯 AI विश्वास स्कोर',
        'severity_lbl':'गंभीरता','est_treatment_cost':'अनुमानित उपचार लागत',
        'also_affects':'⚠️ इन फसलों को भी प्रभावित करता है',
        'chemical_treatment':'💊 रासायनिक उपचार',
        'organic_option_tab':'🌿 जैविक विकल्प',
        'prevention_tab':'🛡️ रोकथाम',
        'spray_schedule':'🗓️ दिन-दर-दिन स्प्रे कार्यक्रम',
        'share_whatsapp':'WhatsApp पर शेयर करें',
        'download_pdf_report':'📥 PDF रिपोर्ट डाउनलोड',
        'share_actions':'📤 शेयर और कार्रवाई',
        'upload_prompt':'रोग पहचानने के लिए पत्ती की तस्वीर अपलोड करें',
        'day_lbl':'दिन','action_lbl':'कार्रवाई','product_lbl':'उत्पाद','time_lbl':'समय',
    },
    'te': {
        'home':'హోమ్','crop_ideas':'పంట ఆలోచనలు','disease_prediction':'వ్యాధి నిర్ధారణ',
        'schemes':'ప్రభుత్వ పథకాలు','help':'సహాయం','profile':'ప్రొఫైల్',
        'logout':'లాగ్అవుట్','welcome':'స్వాగతం','login':'లాగిన్','register':'నమోదు',
        'select_language':'భాష ఎంచుకోండి','continue':'కొనసాగించు',
        'upload_soil':'మట్టి చిత్రం అప్లోడ్ చేయండి','select_state':'రాష్ట్రం ఎంచుకోండి',
        'select_district':'జిల్లా ఎంచుకోండి','select_season':'సీజన్ ఎంచుకోండి',
        'analyze':'మట్టిని విశ్లేషించండి','soil_type':'మట్టి రకం',
        'soil_features':'మట్టి లక్షణాలు','recommended_crops':'సిఫార్సు చేసిన పంటలు',
        'vegetables':'కూరగాయలు','fruits':'పండ్లు','flowers':'పూలు','indoor_plants':'ఇండోర్ మొక్కలు',
        'market_demand':'మార్కెట్ డిమాండ్','high':'అధిక','medium':'మధ్యస్థ','low':'తక్కువ',
        'upload_leaf':'ఆకు చిత్రం అప్లోడ్ చేయండి','detect_disease':'వ్యాధిని గుర్తించండి',
        'disease_name':'వ్యాధి పేరు','treatment':'చికిత్స','prevention':'నివారణ',
        'all_schemes':'అన్ని పథకాలు','central_govt':'కేంద్ర ప్రభుత్వం','state_govt':'రాష్ట్ర ప్రభుత్వం',
        'benefits':'ప్రయోజనాలు','eligibility':'అర్హత','apply_now':'దరఖాస్తు చేయండి',
        'view_details':'వివరాలు చూడండి','search_schemes':'పథకాలు వెతకండి...',
        'contact_us':'సంప్రదించండి','your_name':'మీ పేరు','your_email':'మీ ఇమెయిల్',
        'your_message':'మీ సందేశం','send_message':'సందేశం పంపండి',
        'faq':'తరచుగా అడిగే ప్రశ్నలు','submit':'సమర్పించండి',
        'kharif':'ఖరీఫ్ (జూన్-అక్టోబర్)','rabi':'రబీ (నవంబర్-మార్చి)','zaid':'జైద్ (ఏప్రిల్-జూన్)',
        'health_score':'మట్టి ఆరోగ్య స్కోర్','confidence':'నమ్మకం','cause':'కారణం',
        'organic_option':'సేంద్రీయ వికల్పం','dashboard':'డాష్బోర్డ్',
        'download_report':'PDF నివేదిక డౌన్‌లోడ్','market':'🛒 అగ్రిమార్ట్','market_prices':'మార్కెట్ ధరలు',
        'forgot_password':'పాస్వర్డ్ మర్చిపోయారా?','reset_password':'పాస్వర్డ్ రీసెట్',
        'change_password':'పాస్వర్డ్ మార్చండి','upload_photo':'ఫోటో అప్లోడ్ చేయండి',
        'notifications':'నోటిఫికేషన్లు','unread':'చదవని సందేశాలు',
        'image_error':'దయచేసి చెల్లుబాటు అయ్యే చిత్రం అప్లోడ్ చేయండి (JPG, PNG)',
        'subject':'విషయం','admin_panel':'అడ్మిన్ పేనల్','district_crops_title': 'జిల్లాలో సిఫార్సు చేసిన పంటలు',
        'trust_note': 'ఈ పంటలు మీ జిల్లాలో చారిత్రక వ్యవసాయ డేటా ఆధారంగా నిరూపించబడిన విజయవంతమైన పంటలు.',
        # Crop Ideas - new features
        'weather_intel':'వాతావరణ సమాచారం',
        'temperature':'ఉష్ణోగ్రత','rainfall':'వర్షపాతం',
        'humidity':'తేమ','drought_risk':'కరువు ప్రమాదం',
        'drought_alert':'⚠️ అధిక కరువు ప్రమాదం! తక్కువ వర్షపాతం అంచనా. కరువు-నిరోధక పంటలకు ప్రాధాన్యత.',
        'top_recommendation':'⭐ అగ్ర సిఫార్సు',
        'based_on_ai':'మట్టి + వాతావరణం + లాభం విశ్లేషణ ఆధారంగా',
        'est_profit':'అంచనా లాభం/ఎకరా','risk_score':'ప్రమాద స్కోర్','water_need':'నీటి అవసరం',
        'recommended_crops_for':'సిఫార్సు చేసిన పంటలు',
        'compare_crops':'📊 అన్ని పంటలు పోల్చండి',
        'compare_table':'📊 పంట పోలిక పట్టిక',
        'investment':'పెట్టుబడి/ఎకరా','revenue':'ఆదాయం/ఎకరా',
        'profit_acre':'లాభం/ఎకరా','season_ok':'సీజన్ సరైనది',
        'in_season':'✅ సీజన్‌లో','off_season':'⚠️ సీజన్ కాదు','drought_ok':'కరువు సరే',
        'ai_risk_score':'🧠 AI ప్రమాద స్కోర్','click_calendar':'📅 క్యాలెండర్ కోసం క్లిక్ చేయండి',
        'farming_calendar':'📅 వ్యవసాయ క్యాలెండర్','download_pdf_cal':'📥 PDF క్యాలెండర్ డౌన్‌లోడ్',
        'soil_health_plan':'🧪 మట్టి ఆరోగ్య మెరుగుదల ప్రణాళిక',
        'req_fertilizers':'⚗️ అవసరమైన ఎరువులు','organic_compost':'🌿 సేంద్రీయ కంపోస్ట్',
        'crop_rotation':'🔄 పంట మార్పిడి ప్రణాళిక','green_manure':'🌿 హరిత ఎరువు',
        'alt_crops':'🌾 ప్రత్యామ్నాయ పంట సూచనలు',
        'alt_crops_note':'మీ ప్రాథమిక పంట విఫలమైతే, ఇవి తక్కువ ప్రమాదంతో ఉంటాయి.',
        'success_story':'📍 సమీప రైతు విజయగాథ',
        'farmers_succeeded':'% రైతులు విజయం సాధించారు','avg_profit':'💰 సగటు లాభం',
        'expert_consult':'🧑‍🌾 నిపుణుల సంప్రదింపు',
        'ai_chatbot':'AI చాట్‌బాట్','ask_ai_btn':'💬 AI అడగండి',
        'kisan_helpline':'కిసాన్ హెల్ప్‌లైన్','submit_query':'సందేహం పంపండి',
        'submit_query_btn':'📝 సందేహం పంపండి','voice_guidance':'🔊 వాయిస్ మార్గదర్శనం',
        'enter_farm_details':'📋 పొలం వివరాలు నమోదు చేయండి',
        'farm_size':'📐 పొలం పరిమాణం (ఎకరాలు)','soil_image':'📸 మట్టి చిత్రం',
        'analyze_btn':'🔍 విశ్లేషించి సిఫార్సులు పొందండి',
        'health_score_lbl':'ఆరోగ్య స్కోర్',
        # Disease - new features
        'upload_leaf_img':'📸 ఆకు చిత్రం అప్లోడ్ చేయండి',
        'click_upload':'ఆకు ఫోటో కోసం క్లిక్ చేయండి',
        'detect_btn':'🔍 వ్యాధిని గుర్తించండి',
        'recent_detections':'🕐 ఇటీవలి గుర్తింపులు',
        'ai_confidence':'🎯 AI నమ్మకం స్కోర్',
        'severity_lbl':'తీవ్రత','est_treatment_cost':'అంచనా చికిత్స వ్యయం',
        'also_affects':'⚠️ ఈ పంటలను కూడా ప్రభావితం చేస్తుంది',
        'chemical_treatment':'💊 రసాయన చికిత్స',
        'organic_option_tab':'🌿 సేంద్రీయ వికల్పం',
        'prevention_tab':'🛡️ నివారణ',
        'spray_schedule':'🗓️ రోజువారీ స్ప్రే షెడ్యూల్',
        'share_whatsapp':'WhatsApp లో షేర్ చేయండి',
        'download_pdf_report':'📥 PDF నివేదిక డౌన్‌లోడ్',
        'share_actions':'📤 షేర్ & చర్యలు',
        'upload_prompt':'వ్యాధిని గుర్తించడానికి ఆకు చిత్రం అప్లోడ్ చేయండి',
        'day_lbl':'రోజు','action_lbl':'చర్య','product_lbl':'ఉత్పత్తి','time_lbl':'సమయం',
    }
}

def t(key):
    lang = session.get('language', 'en')
    return TRANSLATIONS.get(lang, TRANSLATIONS['en']).get(key, key)

def translate_state(name):
    lang = session.get('language', 'en')
    return STATES_DISPLAY.get(lang, STATES_DISPLAY['en']).get(name, name)

def translate_district(name):
    lang = session.get('language', 'en')
    return DISTRICTS_DISPLAY.get(lang, DISTRICTS_DISPLAY['en']).get(name, name)

def translate_crop(name):
    lang = session.get('language', 'en')
    crop_names = {
        'hi': {
            'Tomato':'टमाटर','Brinjal':'बैंगन','Chilli':'मिर्च','Groundnut':'मूंगफली',
            'Mango':'आम','Papaya':'पपीता','Guava':'अमरूद','Marigold':'गेंदा','Rose':'गुलाब',
            'Aloe Vera':'एलोवेरा','Onion':'प्याज','Garlic':'लहसुन','Soybean':'सोयाबीन',
            'Banana':'केला','Orange':'संतरा','Jasmine':'चमेली','Rice':'चावल','Sugarcane':'गन्ना',
            'Maize':'मक्का','Mustard':'सरसों','Litchi':'लीची','Wheat':'गेहूं','Carrot':'गाजर',
            'Watermelon':'तरबूज','Cotton':'कपास','Jute':'जूट','Millet':'बाजरा','Fern':'फर्न',
            'Plum':'बेर','Tuberose':'रजनीगंधा','Jackfruit':'कटहल','Sweet Lime':'मीठा नींबू',
            'Chrysanthemum':'गुलदाउदी','Snake Plant':'सांप का पौधा','Peace Lily':'पीस लिली',
            'Bamboo Plant':'बांस का पौधा','Rubber Plant':'रबर का पौधा','Gladiolus':'ग्लेडियोलस',
            'Potato':'आलू','Pepper':'शिमला मिर्च','Eggplant':'बैंगन','Tomatillo':'टोमेटिलो',
            'Barley':'जौ','Finger Millet':'रागी','Foxtail Millet':'कंगनी','Coffee':'कॉफी',
            'Bean':'सेम','Bitter Gourd':'करेला','Okra':'भिंडी','Mung Bean':'मूंग',
            'Black Gram':'उड़द','Ginger':'अदरक',
            # NEW — district crops
            'Paddy':'धान','Redgram':'अरहर दाल','Chickpea':'चना',
            'Sunflower':'सूरजमुखी','Safflower':'कुसुम','Moong':'मूंग',
            'Sesame':'तिल','Turmeric':'हल्दी','Tobacco':'तंबाकू',
            'Cashew':'काजू','Ragi':'रागी','Bajra':'बाजरा','Jowar':'ज्वार',
            'Horsegram':'कुलथी','Guar':'ग्वार','Moth Bean':'मोठ',
            'Cumin':'जीरा','Coriander':'धनिया','Pea':'मटर',
            'Castor':'अरंडी','Arecanut':'सुपारी','Coconut':'नारियल',
            'Grapes':'अंगूर','Tur':'तुअर',
            'Flowers':'फूल','Vegetables':'सब्जियां',
            'Leafy Greens':'हरी पत्तेदार सब्जियां',
            'Leafy Vegetables':'पत्तेदार सब्जियां',
        },
        'te': {
            'Tomato':'టమాటా','Brinjal':'వంకాయ','Chilli':'మిర్చి','Groundnut':'వేరుశెనగ',
            'Mango':'మామిడి','Papaya':'బొప్పాయి','Guava':'జామ','Marigold':'చేమంతి','Rose':'గులాబి',
            'Aloe Vera':'అలోవెరా','Onion':'ఉల్లి','Garlic':'వెల్లుల్లి','Soybean':'సోయాబీన్',
            'Banana':'అరటి','Orange':'నారింజ','Jasmine':'మల్లె','Rice':'వరి','Sugarcane':'చెరకు',
            'Maize':'మొక్కజొన్న','Mustard':'ఆవాలు','Litchi':'లీచీ','Wheat':'గోధుమ','Carrot':'క్యారెట్',
            'Watermelon':'పుచ్చకాయ','Cotton':'పత్తి','Jute':'జనపనార','Millet':'జొన్న','Fern':'ఫెర్న్',
            'Plum':'ప్లమ్','Tuberose':'సుగంధరాజ','Jackfruit':'పనస','Sweet Lime':'మీడి నిమ్మ',
            'Chrysanthemum':'సేవంతి','Snake Plant':'స్నేక్ ప్లాంట్','Peace Lily':'పీస్ లిలీ',
            'Bamboo Plant':'వెదురు మొక్క','Rubber Plant':'రబ్బరు మొక్క','Gladiolus':'గ్లాడియోలస్',
            'Potato':'బంగాళాదుంప','Pepper':'మిరపకాయ','Eggplant':'వంకాయ','Tomatillo':'టొమాటిల్లో',
            'Barley':'బార్లీ','Finger Millet':'రాగి','Foxtail Millet':'కొర్రలు','Coffee':'కాఫీ',
            'Bean':'బీన్స్','Bitter Gourd':'కాకర','Okra':'బెండ','Mung Bean':'పెసలు',
            'Black Gram':'మినుములు','Ginger':'అల్లం',
             # NEW — district crops
            'Paddy':'వరి','Redgram':'కందులు','Chickpea':'శనగలు',
            'Sunflower':'పొద్దుతిరుగుడు','Safflower':'కుసుమ','Moong':'పెసలు',
            'Sesame':'నువ్వులు','Turmeric':'పసుపు','Tobacco':'పొగాకు',
            'Cashew':'జీడిపప్పు','Ragi':'రాగి','Bajra':'సజ్జలు','Jowar':'జొన్న',
            'Horsegram':'అలసంద','Guar':'గోరుచిక్కుడు','Moth Bean':'మోత్ బీన్',
            'Cumin':'జీలకర్ర','Coriander':'కొత్తిమీర','Pea':'బఠాణీ',
            'Castor':'ఆముదం','Arecanut':'వక్కపోక','Coconut':'కొబ్బరి',
            'Grapes':'ద్రాక్ష','Tur':'కందులు',
            'Flowers':'పూలు','Vegetables':'కూరగాయలు',
            'Leafy Greens':'ఆకు కూరలు',
            'Leafy Vegetables':'ఆకు కూరలు',
        }
    }
    return crop_names.get(lang, {}).get(name, name)

def translate_disease(name):
    lang = session.get('language', 'en')
    disease_names = {
        'hi': {
            'Tomato Late Blight':'टमाटर लेट ब्लाइट','Rice Blast':'धान का झुलसा',
            'Powdery Mildew':'पाउडरी फफूंद','Leaf Rust':'पत्ती का जंग',
            'Bacterial Wilt':'बैक्टीरियल विल्ट','Yellow Mosaic Virus':'पीला मोजेक वायरस'
        },
        'te': {
            'Tomato Late Blight':'టమాటా ఆలస్య తెగులు','Rice Blast':'వరి బ్లాస్ట్',
            'Powdery Mildew':'పొడి తెగులు','Leaf Rust':'ఆకు తుప్పు',
            'Bacterial Wilt':'బాక్టీరియల్ వాడు','Yellow Mosaic Virus':'పసుపు మొజాయిక్ వైరస్'
        }
    }
    return disease_names.get(lang, {}).get(name, name)

app.jinja_env.globals['t'] = t
app.jinja_env.globals['translate_state'] = translate_state
app.jinja_env.globals['translate_district'] = translate_district
app.jinja_env.globals['translate_crop'] = translate_crop
app.jinja_env.globals['translate_disease'] = translate_disease
app.jinja_env.globals['current_year'] = 2026
app.jinja_env.globals['enumerate'] = enumerate

# ─────────────────────────────────────────────
# DATA
# ─────────────────────────────────────────────
# Trilingual state & district names: key=English (used internally), display translated in template

class CommunityPost(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    farmer_id  = db.Column(db.Integer, db.ForeignKey('farmer.id'))
    title      = db.Column(db.String(200))
    body       = db.Column(db.Text)
    crop       = db.Column(db.String(80))
    district   = db.Column(db.String(80))
    image_path = db.Column(db.String(200))
    video_path = db.Column(db.String(200))
    likes      = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    farmer     = db.relationship('Farmer', backref='posts')

class CommunityReply(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    post_id    = db.Column(db.Integer, db.ForeignKey('community_post.id'))
    farmer_id  = db.Column(db.Integer, db.ForeignKey('farmer.id'))
    body       = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    farmer     = db.relationship('Farmer', backref='replies')

class DiseaseAlert(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    disease      = db.Column(db.String(100))
    crop         = db.Column(db.String(80))
    state        = db.Column(db.String(80))
    district     = db.Column(db.String(80))
    severity     = db.Column(db.String(20))
    report_count = db.Column(db.Integer, default=1)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

class NewsAlert(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    title      = db.Column(db.String(300))
    body       = db.Column(db.Text)
    category   = db.Column(db.String(50))
    icon       = db.Column(db.String(10), default='📰')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class BookmarkedDisease(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    farmer_id    = db.Column(db.Integer, db.ForeignKey('farmer.id'))
    detection_id = db.Column(db.Integer, db.ForeignKey('disease_detection.id'))
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)


STATES_DISTRICTS = {
    "Andhra Pradesh": ["Visakhapatnam","Vijayawada","Guntur","Kurnool","Nellore","Tirupati","Anantapur","Kadapa","Eluru","Ongole"],
    "Telangana": ["Adilabad","Bhadradri Kothagudem","Hanamkonda","Hyderabad","Jagtial","Jangaon","Jayashankar Bhupalpally","Jogulamba Gadwal",
                  "Kamareddy","Karimnagar","Khammam","Komaram Bheem Asifabad","Mahabubabad","Mahabubnagar","Mancherial","Medak","Medchal-Malkajgiri",
                  "Mulugu","Nagarkurnool","Nalgonda","Narayanpet","Nirmal","Nizamabad","Peddapalli","Rajanna Sircilla","Rangareddy","Sangareddy","Siddipet","Suryapet","Vikarabad","Wanaparthy","Warangal","Yadadri Bhuvanagiri"],
    "Maharashtra": ["Mumbai","Pune","Nagpur","Nashik","Aurangabad","Solapur","Kolhapur","Amravati","Sangli","Latur"],
    "Karnataka": ["Bengaluru","Mysuru","Hubli","Mangaluru","Belagavi","Dharwad","Vijayapura","Davanagere","Shimoga","Tumkur"],
    "Tamil Nadu": ["Chennai","Coimbatore","Madurai","Salem","Trichy","Tirunelveli","Vellore","Erode","Dindigul","Thanjavur"],
    "Uttar Pradesh": ["Lucknow","Kanpur","Agra","Varanasi","Allahabad","Meerut","Ghaziabad","Gorakhpur","Aligarh","Moradabad"],
    "Punjab": ["Ludhiana","Amritsar","Jalandhar","Patiala","Bathinda","Mohali","Pathankot","Hoshiarpur","Gurdaspur","Firozpur"],
    "Rajasthan": ["Jaipur","Jodhpur","Udaipur","Kota","Bikaner","Ajmer","Bhilwara","Alwar","Bharatpur","Sikar"],
    "Madhya Pradesh": ["Bhopal","Indore","Gwalior","Jabalpur","Ujjain","Sagar","Rewa","Satna","Dewas","Chhindwara"],
    "Gujarat": ["Ahmedabad","Surat","Vadodara","Rajkot","Bhavnagar","Jamnagar","Gandhinagar","Anand","Mehsana","Junagadh"],
}

# Trilingual display names for states
STATES_DISPLAY = {
    "en": {
        "Andhra Pradesh":"Andhra Pradesh","Telangana":"Telangana","Maharashtra":"Maharashtra",
        "Karnataka":"Karnataka","Tamil Nadu":"Tamil Nadu","Uttar Pradesh":"Uttar Pradesh",
        "Punjab":"Punjab","Rajasthan":"Rajasthan","Madhya Pradesh":"Madhya Pradesh","Gujarat":"Gujarat"
    },
    "hi": {
        "Andhra Pradesh":"आंध्र प्रदेश","Telangana":"तेलंगाना","Maharashtra":"महाराष्ट्र",
        "Karnataka":"कर्नाटक","Tamil Nadu":"तमिलनाडु","Uttar Pradesh":"उत्तर प्रदेश",
        "Punjab":"पंजाब","Rajasthan":"राजस्थान","Madhya Pradesh":"मध्य प्रदेश","Gujarat":"गुजरात"
    },
    "te": {
        "Andhra Pradesh":"ఆంధ్రప్రదేశ్","Telangana":"తెలంగాణ","Maharashtra":"మహారాష్ట్ర",
        "Karnataka":"కర్ణాటక","Tamil Nadu":"తమిళనాడు","Uttar Pradesh":"ఉత్తరప్రదేశ్",
        "Punjab":"పంజాబ్","Rajasthan":"రాజస్థాన్","Madhya Pradesh":"మధ్యప్రదేశ్","Gujarat":"గుజరాత్"
    }
}

# Trilingual district names
DISTRICTS_DISPLAY = {
    "en": {d:d for state_dists in [
        ["Visakhapatnam","Vijayawada","Guntur","Kurnool","Nellore","Tirupati","Anantapur","Kadapa","Eluru","Ongole",
         "Adilabad","Bhadradri Kothagudem","Hanamkonda","Hyderabad","Jagtial","Jangaon","Jayashankar Bhupalpally",
         "Jogulamba Gadwal","Kamareddy","Karimnagar","Khammam","Komaram Bheem Asifabad","Mahabubabad","Mahabubnagar",
         "Mancherial","Medak","Medchal-Malkajgiri","Mulugu","Nagarkurnool","Nalgonda","Narayanpet","Nirmal","Nizamabad",
         "Peddapalli","Rajanna Sircilla","Rangareddy","Sangareddy","Siddipet","Suryapet","Vikarabad","Wanaparthy","Warangal","Yadadri Bhuvanagiri",
         "Mumbai","Pune","Nagpur","Nashik","Aurangabad","Solapur","Kolhapur","Amravati","Sangli","Latur",
         "Bengaluru","Mysuru","Hubli","Mangaluru","Belagavi","Dharwad","Vijayapura","Davanagere","Shimoga","Tumkur",
         "Chennai","Coimbatore","Madurai","Salem","Trichy","Tirunelveli","Vellore","Erode","Dindigul","Thanjavur",
         "Lucknow","Kanpur","Agra","Varanasi","Allahabad","Meerut","Ghaziabad","Gorakhpur","Aligarh","Moradabad",
         "Ludhiana","Amritsar","Jalandhar","Patiala","Bathinda","Mohali","Pathankot","Hoshiarpur","Gurdaspur","Firozpur",
         "Jaipur","Jodhpur","Udaipur","Kota","Bikaner","Ajmer","Bhilwara","Alwar","Bharatpur","Sikar",
         "Bhopal","Indore","Gwalior","Jabalpur","Ujjain","Sagar","Rewa","Satna","Dewas","Chhindwara",
         "Ahmedabad","Surat","Vadodara","Rajkot","Bhavnagar","Jamnagar","Gandhinagar","Anand","Mehsana","Junagadh"]
    ] for d in state_dists},
    "hi": {
        "Visakhapatnam":"विशाखापटनम","Vijayawada":"विजयवाड़ा","Guntur":"गुंटूर","Kurnool":"कुरनूल",
        "Nellore":"नेल्लोर","Tirupati":"तिरुपति","Anantapur":"अनंतपुर","Kadapa":"कडपा","Eluru":"एलुरु","Ongole":"ओंगोल",
        "Adilabad":"आदिलाबाद","Bhadradri Kothagudem":"भद्राद्री कोठागुडेम","Hanamkonda":"हनमकोंडा","Hyderabad":"हैदराबाद",
        "Jagtial":"जगतियाल","Jangaon":"जनगांव","Jayashankar Bhupalpally":"जयशंकर भूपालपल्ली","Jogulamba Gadwal":"जोगुलाम्बा गडवाल",
        "Kamareddy":"कामारेड्डी","Karimnagar":"करीमनगर","Khammam":"खम्मम","Komaram Bheem Asifabad":"कोमाराम भीम आसिफाबाद",
        "Mahabubabad":"महबूबाबाद","Mahabubnagar":"महबूबनगर","Mancherial":"मंचेरियल","Medak":"मेडक","Medchal-Malkajgiri":"मेडचल-मल्काजगिरि",
        "Mulugu":"मुलुगु","Nagarkurnool":"नागरकुरनूल","Nalgonda":"नालगोंडा","Narayanpet":"नारायणपेट","Nirmal":"निर्मल",
        "Nizamabad":"निज़ामाबाद","Peddapalli":"पेड्डापल्ली","Rajanna Sircilla":"राजन्ना सिरसिल्ला","Rangareddy":"रंगारेड्डी",
        "Sangareddy":"संगारेड्डी","Siddipet":"सिद्दिपेट","Suryapet":"सूर्यापेट","Vikarabad":"विकाराबाद","Wanaparthy":"वनपर्थी",
        "Warangal":"वारंगल","Yadadri Bhuvanagiri":"यदाद्री भुवनगिरि",
        "Mumbai":"मुंबई","Pune":"पुणे","Nagpur":"नागपुर","Nashik":"नासिक","Aurangabad":"औरंगाबाद",
        "Solapur":"सोलापुर","Kolhapur":"कोल्हापुर","Amravati":"अमरावती","Sangli":"सांगली","Latur":"लातूर",
        "Bengaluru":"बेंगलुरु","Mysuru":"मैसूरु","Hubli":"हुबली","Mangaluru":"मंगलुरु","Belagavi":"बेलगावी",
        "Dharwad":"धारवाड़","Vijayapura":"विजयपुर","Davanagere":"दावणगेरे","Shimoga":"शिमोगा","Tumkur":"तुमकुर",
        "Chennai":"चेन्नई","Coimbatore":"कोयंबटूर","Madurai":"मदुरै","Salem":"सेलम","Trichy":"त्रिची",
        "Tirunelveli":"तिरुनेलवेली","Vellore":"वेल्लोर","Erode":"इरोड","Dindigul":"डिंडीगुल","Thanjavur":"तंजावुर",
        "Lucknow":"लखनऊ","Kanpur":"कानपुर","Agra":"आगरा","Varanasi":"वाराणसी","Allahabad":"इलाहाबाद",
        "Meerut":"मेरठ","Ghaziabad":"गाजियाबाद","Gorakhpur":"गोरखपुर","Aligarh":"अलीगढ","Moradabad":"मुरादाबाद",
        "Ludhiana":"लुधियाना","Amritsar":"अमृतसर","Jalandhar":"जालंधर","Patiala":"पटियाला","Bathinda":"बठिंडा",
        "Mohali":"मोहाली","Pathankot":"पठानकोट","Hoshiarpur":"होशियारपुर","Gurdaspur":"गुरदासपुर","Firozpur":"फिरोजपुर",
        "Jaipur":"जयपुर","Jodhpur":"जोधपुर","Udaipur":"उदयपुर","Kota":"कोटा","Bikaner":"बीकानेर",
        "Ajmer":"अजमेर","Bhilwara":"भीलवाड़ा","Alwar":"अलवर","Bharatpur":"भरतपुर","Sikar":"सीकर",
        "Bhopal":"भोपाल","Indore":"इंदौर","Gwalior":"ग्वालियर","Jabalpur":"जबलपुर","Ujjain":"उज्जैन",
        "Sagar":"सागर","Rewa":"रीवा","Satna":"सतना","Dewas":"देवास","Chhindwara":"छिंदवाड़ा",
        "Ahmedabad":"अहमदाबाद","Surat":"सूरत","Vadodara":"वडोदरा","Rajkot":"राजकोट","Bhavnagar":"भावनगर",
        "Jamnagar":"जामनगर","Gandhinagar":"गांधीनगर","Anand":"आनंद","Mehsana":"मेहसाणा","Junagadh":"जूनागढ़"
    },
    "te": {
        "Visakhapatnam":"విశాఖపట్నం","Vijayawada":"విజయవాడ","Guntur":"గుంటూరు","Kurnool":"కర్నూలు",
        "Nellore":"నెల్లూరు","Tirupati":"తిరుపతి","Anantapur":"అనంతపురం","Kadapa":"కడప","Eluru":"ఏలూరు","Ongole":"ఒంగోలు",
        "Adilabad":"ఆదిలాబాద్","Bhadradri Kothagudem":"భద్రాద్రి కొత్తగూడెం","Hanamkonda":"హనమకొండ","Hyderabad":"హైదరాబాద్",
        "Jagtial":"జగిత్యాల","Jangaon":"జనగామ","Jayashankar Bhupalpally":"జయశంకర్ భూపాలపల్లి","Jogulamba Gadwal":"జోగులాంబ గద్వాల",
        "Kamareddy":"కామారెడ్డి","Karimnagar":"కరీంనగర్","Khammam":"ఖమ్మం","Komaram Bheem Asifabad":"కొమురంభీమ్ ఆసిఫాబాద్",
        "Mahabubabad":"మహబూబాబాద్","Mahabubnagar":"మహబూబ్‌నగర్","Mancherial":"మంచిర్యాల","Medak":"మెదక్","Medchal-Malkajgiri":"మేడ్చల్-మల్కాజ్‌గిరి",
        "Mulugu":"ములుగు","Nagarkurnool":"నాగర్‌కర్నూల్","Nalgonda":"నల్గొండ","Narayanpet":"నారాయణపేట","Nirmal":"నిర్మల్",
        "Nizamabad":"నిజామాబాద్","Peddapalli":"పెద్దపల్లి","Rajanna Sircilla":"రాజన్న సిరిసిల్ల","Rangareddy":"రంగారెడ్డి",
        "Sangareddy":"సంగారెడ్డి","Siddipet":"సిద్దిపేట","Suryapet":"సూర్యాపేట","Vikarabad":"వికారాబాద్","Wanaparthy":"వనపర్తి",
        "Warangal":"వరంగల్","Yadadri Bhuvanagiri":"యాదాద్రి భువనగిరి",
        "Mumbai":"ముంబై","Pune":"పూణె","Nagpur":"నాగపూర్","Nashik":"నాసిక్","Aurangabad":"ఔరంగాబాద్",
        "Solapur":"సోలాపూర్","Kolhapur":"కొల్హాపూర్","Amravati":"అమరావతి","Sangli":"సాంగ్లి","Latur":"లాతూర్",
        "Bengaluru":"బెంగళూరు","Mysuru":"మైసూరు","Hubli":"హుబ్లి","Mangaluru":"మంగళూరు","Belagavi":"బెళగావి",
        "Dharwad":"ధార్వాడ","Vijayapura":"విజయపుర","Davanagere":"దావణగెరె","Shimoga":"శివమొగ్గ","Tumkur":"తుమకూరు",
        "Chennai":"చెన్నై","Coimbatore":"కోయంబత్తూర్","Madurai":"మధురై","Salem":"సేలం","Trichy":"తిరుచిరాపల్లి",
        "Tirunelveli":"తిరునేల్వేలి","Vellore":"వేలూరు","Erode":"ఈరోడ్","Dindigul":"దిండిగల్","Thanjavur":"తంజావూరు",
        "Lucknow":"లక్నో","Kanpur":"కాన్పూర్","Agra":"ఆగ్రా","Varanasi":"వారణాసి","Allahabad":"అలహాబాద్",
        "Meerut":"మీరట్","Ghaziabad":"గాజియాబాద్","Gorakhpur":"గోరఖ్‌పూర్","Aligarh":"అలీగఢ్","Moradabad":"మొరాదాబాద్",
        "Ludhiana":"లూధియానా","Amritsar":"అమృత్‌సర్","Jalandhar":"జలంధర్","Patiala":"పటియాలా","Bathinda":"బఠిండా",
        "Mohali":"మొహాలి","Pathankot":"పఠాన్‌కోట్","Hoshiarpur":"హోషియార్‌పూర్","Gurdaspur":"గురుదాస్‌పూర్","Firozpur":"ఫిరోజ్‌పూర్",
        "Jaipur":"జైపూర్","Jodhpur":"జోధ్‌పూర్","Udaipur":"ఉదయపూర్","Kota":"కోటా","Bikaner":"బికానేర్",
        "Ajmer":"అజ్మీర్","Bhilwara":"భీల్వాడా","Alwar":"అల్వార్","Bharatpur":"భరత్‌పూర్","Sikar":"సీకర్",
        "Bhopal":"భోపాల్","Indore":"ఇండోర్","Gwalior":"గ్వాలియర్","Jabalpur":"జబల్‌పూర్","Ujjain":"ఉజ్జయిని",
        "Sagar":"సాగర్","Rewa":"రీవా","Satna":"సత్నా","Dewas":"దేవాస్","Chhindwara":"ఛిందవాడా",
        "Ahmedabad":"అహ్మదాబాద్","Surat":"సూరత్","Vadodara":"వడోదర","Rajkot":"రాజ్‌కోట్","Bhavnagar":"భావనగర్",
        "Jamnagar":"జామ్‌నగర్","Gandhinagar":"గాంధీనగర్","Anand":"ఆనంద్","Mehsana":"మెహసానా","Junagadh":"జునాగఢ్"
    }
}

SOIL_DATA = {
    "Alluvial Soil": {
        "features": {
            "en": "MOST FERTILE soil! Rich in potash, phosphoric acid & lime, excellent for agriculture, found near river banks, pH 7.0-8.0, supports diverse crops",
            "hi": "सबसे उपजाऊ मिट्टी! पोटाश, फॉस्फोरिक एसिड और चूने से भरपूर, नदी किनारों के पास, pH 7.0-8.0",
            "te": "అత్యంత సారవంతమైన మట్టి! పొటాష్, ఫాస్ఫోరిక్ ఆమ్లం & సున్నంతో సమృద్ధి, నదీ తీరాల దగ్గర, pH 7.0-8.0"
        },
        "health_score": 9.5,
        
        "nitrogen": "Very High (280–350 kg/ha)*", "phosphorus": "High (22–32 kg/ha)*", "potassium": "Very High (380–450 kg/ha)*", "ph": "6.8–7.5 (typical range)*",
        "recommendation": "Minimal inputs needed. Maintain with light compost applications. Suitable for all crops.",
        "crops": {
            "vegetables": [{"name":"Sugarcane","demand":"high","price":4},{"name":"Maize","demand":"high","price":20},{"name":"Mustard","demand":"high","price":55},{"name":"Jute","demand":"medium","price":42}],
            "fruits": [{"name":"Litchi","demand":"high","price":80},{"name":"Mango","demand":"high","price":60},{"name":"Jackfruit","demand":"medium","price":25}],
            "flowers": [{"name":"Tuberose","demand":"high","price":60},{"name":"Gladiolus","demand":"medium","price":80}],
            "indoor": [{"name":"Bamboo Plant","demand":"high","price":100},{"name":"Peace Lily","demand":"medium","price":120}]
        }
    },
    "Black Soil": {
        "features": {
            "en": "Rich in Calcium, Magnesium & Iron, low in Nitrogen & Phosphorus, high water retention, excellent for cotton & soybean, pH 7.5-8.5",
            "hi": "कैल्शियम, मैग्नीशियम और आयरन से भरपूर, नाइट्रोजन और फास्फोरस में कम, उच्च जल धारण, कपास के लिए उत्तम, pH 7.5-8.5",
            "te": "కాల్షియం, మెగ్నీషియం & ఇనుముతో సమృద్ధి, నైట్రోజన్ తక్కువ, నీటి నిలుపుదల అధికం, పత్తికి అనుకూలం, pH 7.5-8.5"
        },
        "health_score": 7.8,
        "nitrogen": "Medium (190–250 kg/ha)*", "phosphorus": "Medium (15–22 kg/ha)*", "potassium": "High (300–400 kg/ha)*", "ph": "7.5–8.5 (typical range)*",
        "recommendation": "Add gypsum to reduce pH. Apply Phosphorus fertilizer. Excellent for cotton and soybean.",
        "crops": {
            "vegetables": [{"name":"Onion","demand":"high","price":30},{"name":"Garlic","demand":"high","price":80},{"name":"Soybean","demand":"high","price":45}],
            "fruits": [{"name":"Banana","demand":"high","price":35},{"name":"Orange","demand":"medium","price":40},{"name":"Sweet Lime","demand":"medium","price":35}],
            "flowers": [{"name":"Jasmine","demand":"high","price":200},{"name":"Chrysanthemum","demand":"medium","price":40}],
            "indoor": [{"name":"Peace Lily","demand":"medium","price":120},{"name":"Snake Plant","demand":"high","price":80}]
        }
    },
    "Clay Soil": {
        "features": {
            "en": "High nutrient content, poor drainage, heavy when wet, needs organic matter to improve structure, pH 6.0-7.5, add sand to improve drainage",
            "hi": "उच्च पोषक तत्व, खराब जल निकासी, गीला होने पर भारी, संरचना सुधारने के लिए जैविक पदार्थ, जल निकासी के लिए रेत डालें",
            "te": "అధిక పోషకాలు, నీటి పారుదల తక్కువ, తడిగా ఉన్నప్పుడు భారంగా, సేంద్రీయ పదార్థం అవసరం, నీటి పారుదలకు ఇసుక జోడించండి"
        },
        "health_score": 6.8,
       "nitrogen": "High (240–280 kg/ha)*", "phosphorus": "Medium (18–24 kg/ha)*", "potassium": "High (300–340 kg/ha)*", "ph": "6.0–7.5 (typical range)*",
        "recommendation": "Mix sand and organic matter to improve drainage. Avoid overwatering. Good for paddy cultivation.",
        "crops": {
            "vegetables": [{"name":"Rice","demand":"high","price":35},{"name":"Broccoli","demand":"medium","price":40},{"name":"Lettuce","demand":"medium","price":30}],
            "fruits": [{"name":"Plum","demand":"medium","price":70},{"name":"Cherry","demand":"high","price":300}],
            "flowers": [{"name":"Iris","demand":"medium","price":100},{"name":"Aster","demand":"low","price":40}],
            "indoor": [{"name":"Fern","demand":"medium","price":80},{"name":"Rubber Plant","demand":"high","price":200}]
        }
    },
    "Red Soil": {
        "features": {
            "en": "Low in Nitrogen & Phosphorus, High Iron content, slightly acidic pH (5.5-6.5), good drainage, needs organic compost and NPK fertilizer",
            "hi": "नाइट्रोजन और फास्फोरस में कम, उच्च आयरन, थोड़ा अम्लीय pH (5.5-6.5), अच्छी जल निकासी, जैविक खाद और NPK उर्वरक की जरूरत",
            "te": "నైట్రోజన్ & ఫాస్పరస్ తక్కువ, అధిక ఇనుము, pH 5.5-6.5, మంచి నీటి పారుదల, సేంద్రీయ ఎరువు & NPK ఎరువు అవసరం"
        },
        "health_score": 6.5,
        "nitrogen": "Low (150–200 kg/ha)*", "phosphorus": "Low (10–15 kg/ha)*", "potassium": "Medium (250–310 kg/ha)*", "ph": "5.5–6.5 (typical range)*",
        "recommendation": "Apply 2 tons of organic compost per acre before sowing. Use NPK 17:17:17 fertilizer.",
        "crops": {
            "vegetables": [{"name":"Tomato","demand":"high","price":25},{"name":"Brinjal","demand":"medium","price":18},{"name":"Chilli","demand":"high","price":40},{"name":"Groundnut","demand":"high","price":55}],
            "fruits": [{"name":"Mango","demand":"high","price":60},{"name":"Papaya","demand":"medium","price":22},{"name":"Guava","demand":"medium","price":30}],
            "flowers": [{"name":"Marigold","demand":"high","price":20},{"name":"Rose","demand":"high","price":80}],
            "indoor": [{"name":"Aloe Vera","demand":"medium","price":50},{"name":"Money Plant","demand":"low","price":30}]
        }
    }
}

DISTRICT_CROPS = {

    # ══════════════════════════════════════════
    # TELANGANA — all 33 districts
    # ══════════════════════════════════════════
    "Adilabad": {
        "kharif": ["Cotton","Soybean","Redgram","Maize","Paddy"],
        "rabi":   ["Wheat","Chickpea","Sunflower","Safflower","Mustard"],
        "zaid":   ["Groundnut","Moong","Watermelon","Sesame"]
    },
    "Bhadradri Kothagudem": {
        "kharif": ["Paddy","Maize","Cotton","Redgram","Turmeric"],
        "rabi":   ["Chilli","Tomato","Onion","Wheat"],
        "zaid":   ["Watermelon","Moong","Groundnut"]
    },
    "Hanamkonda": {
        "kharif": ["Paddy","Maize","Cotton","Soybean"],
        "rabi":   ["Chilli","Onion","Tomato","Wheat"],
        "zaid":   ["Watermelon","Cucumber","Moong"]
    },
    "Hyderabad": {
        "kharif": ["Tomato","Brinjal","Okra","Maize","Marigold"],
        "rabi":   ["Tomato","Brinjal","Chilli","Onion","Marigold"],
        "zaid":   ["Cucumber","Watermelon","Bitter Gourd","Okra"]
    },
    "Jagtial": {
        "kharif": ["Paddy","Maize","Cotton","Soybean","Redgram"],
        "rabi":   ["Chilli","Turmeric","Onion","Wheat"],
        "zaid":   ["Watermelon","Moong","Groundnut"]
    },
    "Jangaon": {
        "kharif": ["Paddy","Cotton","Maize","Soybean"],
        "rabi":   ["Wheat","Chilli","Onion","Tomato"],
        "zaid":   ["Watermelon","Moong","Sunflower"]
    },
    "Jayashankar Bhupalpally": {
        "kharif": ["Paddy","Maize","Cotton","Redgram"],
        "rabi":   ["Wheat","Chickpea","Sunflower"],
        "zaid":   ["Groundnut","Moong","Watermelon"]
    },
    "Jogulamba Gadwal": {
        "kharif": ["Cotton","Paddy","Maize","Groundnut"],
        "rabi":   ["Wheat","Sunflower","Chickpea","Onion"],
        "zaid":   ["Groundnut","Watermelon","Moong"]
    },
    "Kamareddy": {
        "kharif": ["Paddy","Maize","Cotton","Soybean"],
        "rabi":   ["Wheat","Onion","Tomato","Chilli"],
        "zaid":   ["Watermelon","Moong","Sunflower"]
    },
    "Karimnagar": {
        "kharif": ["Paddy","Maize","Cotton","Soybean","Turmeric"],
        "rabi":   ["Chilli","Turmeric","Onion","Tomato"],
        "zaid":   ["Watermelon","Cucumber","Moong"]
    },
    "Khammam": {
        "kharif": ["Paddy","Cotton","Maize","Chilli","Redgram"],
        "rabi":   ["Chilli","Maize","Tomato","Onion"],
        "zaid":   ["Watermelon","Moong","Groundnut"]
    },
    "Komaram Bheem Asifabad": {
        "kharif": ["Cotton","Soybean","Paddy","Maize","Redgram"],
        "rabi":   ["Wheat","Chickpea","Sunflower"],
        "zaid":   ["Groundnut","Moong","Watermelon"]
    },
    "Mahabubabad": {
        "kharif": ["Paddy","Maize","Cotton","Redgram"],
        "rabi":   ["Wheat","Onion","Chilli","Tomato"],
        "zaid":   ["Watermelon","Moong","Groundnut"]
    },
    "Mahabubnagar": {
        "kharif": ["Cotton","Paddy","Groundnut","Maize","Redgram"],
        "rabi":   ["Wheat","Sunflower","Chickpea","Onion"],
        "zaid":   ["Groundnut","Watermelon","Moong"]
    },
    "Mancherial": {
        "kharif": ["Cotton","Paddy","Maize","Soybean","Redgram"],
        "rabi":   ["Wheat","Chickpea","Sunflower","Onion"],
        "zaid":   ["Groundnut","Watermelon","Moong"]
    },
    "Medak": {
        "kharif": ["Paddy","Maize","Cotton","Soybean"],
        "rabi":   ["Tomato","Onion","Chilli","Wheat"],
        "zaid":   ["Watermelon","Moong","Groundnut"]
    },
    "Medchal-Malkajgiri": {
        "kharif": ["Paddy","Maize","Tomato","Marigold"],
        "rabi":   ["Tomato","Onion","Chilli","Brinjal"],
        "zaid":   ["Cucumber","Watermelon","Moong"]
    },
    "Mulugu": {
        "kharif": ["Paddy","Maize","Redgram","Cotton"],
        "rabi":   ["Wheat","Chickpea","Sunflower"],
        "zaid":   ["Groundnut","Moong","Watermelon"]
    },
    "Nagarkurnool": {
        "kharif": ["Cotton","Paddy","Maize","Groundnut","Redgram"],
        "rabi":   ["Wheat","Sunflower","Chickpea","Onion"],
        "zaid":   ["Groundnut","Watermelon","Moong"]
    },
    "Nalgonda": {
        "kharif": ["Paddy","Cotton","Maize","Groundnut","Redgram"],
        "rabi":   ["Chilli","Tomato","Onion","Wheat"],
        "zaid":   ["Watermelon","Moong","Sunflower"]
    },
    "Narayanpet": {
        "kharif": ["Cotton","Groundnut","Paddy","Maize"],
        "rabi":   ["Wheat","Sunflower","Chickpea","Onion"],
        "zaid":   ["Groundnut","Watermelon","Moong"]
    },
    "Nirmal": {
        "kharif": ["Cotton","Soybean","Paddy","Maize","Redgram"],
        "rabi":   ["Wheat","Chickpea","Sunflower","Onion"],
        "zaid":   ["Groundnut","Moong","Watermelon"]
    },
    "Nizamabad": {
        "kharif": ["Paddy","Maize","Soybean","Cotton","Turmeric"],
        "rabi":   ["Turmeric","Chilli","Wheat","Onion"],
        "zaid":   ["Groundnut","Watermelon","Moong"]
    },
    "Peddapalli": {
        "kharif": ["Paddy","Maize","Cotton","Soybean"],
        "rabi":   ["Chilli","Onion","Wheat","Tomato"],
        "zaid":   ["Watermelon","Moong","Groundnut"]
    },
    "Rajanna Sircilla": {
        "kharif": ["Paddy","Maize","Cotton","Soybean"],
        "rabi":   ["Wheat","Chilli","Onion","Tomato"],
        "zaid":   ["Watermelon","Moong","Sunflower"]
    },
    "Rangareddy": {
        "kharif": ["Paddy","Maize","Tomato","Marigold"],
        "rabi":   ["Tomato","Onion","Chilli","Brinjal"],
        "zaid":   ["Watermelon","Cucumber","Moong"]
    },
    "Sangareddy": {
        "kharif": ["Paddy","Maize","Cotton","Soybean"],
        "rabi":   ["Tomato","Onion","Chilli","Wheat"],
        "zaid":   ["Watermelon","Moong","Sunflower"]
    },
    "Siddipet": {
        "kharif": ["Paddy","Maize","Cotton","Soybean"],
        "rabi":   ["Wheat","Onion","Chilli","Tomato"],
        "zaid":   ["Watermelon","Moong","Groundnut"]
    },
    "Suryapet": {
        "kharif": ["Paddy","Cotton","Maize","Chilli"],
        "rabi":   ["Chilli","Onion","Tomato","Wheat"],
        "zaid":   ["Watermelon","Moong","Groundnut"]
    },
    "Vikarabad": {
        "kharif": ["Paddy","Maize","Cotton","Groundnut"],
        "rabi":   ["Tomato","Onion","Wheat","Chilli"],
        "zaid":   ["Watermelon","Moong","Groundnut"]
    },
    "Wanaparthy": {
        "kharif": ["Cotton","Paddy","Maize","Groundnut"],
        "rabi":   ["Wheat","Sunflower","Onion","Chickpea"],
        "zaid":   ["Groundnut","Watermelon","Moong"]
    },
    "Warangal": {
        "kharif": ["Paddy","Cotton","Maize","Soybean","Turmeric"],
        "rabi":   ["Wheat","Chilli","Onion","Tomato"],
        "zaid":   ["Watermelon","Moong","Groundnut"]
    },
    "Yadadri Bhuvanagiri": {
        "kharif": ["Paddy","Maize","Cotton","Redgram"],
        "rabi":   ["Tomato","Onion","Chilli","Wheat"],
        "zaid":   ["Watermelon","Cucumber","Moong"]
    },

    # ══════════════════════════════════════════
    # ANDHRA PRADESH — 10 districts
    # ══════════════════════════════════════════
    "Visakhapatnam": {
        "kharif": ["Paddy","Maize","Sugarcane","Groundnut","Cashew"],
        "rabi":   ["Wheat","Tomato","Onion","Chilli"],
        "zaid":   ["Watermelon","Moong","Groundnut"]
    },
    "Vijayawada": {
        "kharif": ["Paddy","Maize","Sugarcane","Cotton"],
        "rabi":   ["Chilli","Onion","Tomato","Brinjal"],
        "zaid":   ["Watermelon","Cucumber","Moong"]
    },
    "Guntur": {
        "kharif": ["Chilli","Cotton","Paddy","Maize","Tobacco"],
        "rabi":   ["Chilli","Tobacco","Onion","Tomato"],
        "zaid":   ["Watermelon","Moong","Groundnut"]
    },
    "Kurnool": {
        "kharif": ["Groundnut","Cotton","Paddy","Sunflower","Redgram"],
        "rabi":   ["Groundnut","Wheat","Sunflower","Onion"],
        "zaid":   ["Groundnut","Watermelon","Moong"]
    },
    "Nellore": {
        "kharif": ["Paddy","Sugarcane","Aquaculture","Cotton"],
        "rabi":   ["Paddy","Chilli","Onion","Tomato"],
        "zaid":   ["Watermelon","Moong","Groundnut"]
    },
    "Tirupati": {
        "kharif": ["Groundnut","Paddy","Sugarcane","Cotton"],
        "rabi":   ["Groundnut","Tomato","Chilli","Onion"],
        "zaid":   ["Groundnut","Watermelon","Moong"]
    },
    "Anantapur": {
        "kharif": ["Groundnut","Paddy","Maize","Cotton","Tomato"],
        "rabi":   ["Groundnut","Sunflower","Horsegram","Wheat"],
        "zaid":   ["Groundnut","Watermelon","Moong"]
    },
    "Kadapa": {
        "kharif": ["Groundnut","Paddy","Cotton","Tomato","Onion"],
        "rabi":   ["Groundnut","Onion","Tomato","Chilli"],
        "zaid":   ["Groundnut","Watermelon","Moong"]
    },
    "Eluru": {
        "kharif": ["Paddy","Maize","Sugarcane","Cotton"],
        "rabi":   ["Chilli","Onion","Tomato","Brinjal"],
        "zaid":   ["Watermelon","Cucumber","Moong"]
    },
    "Ongole": {
        "kharif": ["Paddy","Cotton","Maize","Groundnut"],
        "rabi":   ["Chilli","Tomato","Onion","Wheat"],
        "zaid":   ["Watermelon","Moong","Groundnut"]
    },

    # ══════════════════════════════════════════
    # MAHARASHTRA — 10 districts
    # ══════════════════════════════════════════
    "Mumbai": {
        "kharif": ["Tomato","Brinjal","Okra","Marigold"],
        "rabi":   ["Tomato","Brinjal","Onion","Chilli"],
        "zaid":   ["Cucumber","Watermelon","Bitter Gourd"]
    },
    "Pune": {
        "kharif": ["Sugarcane","Tomato","Onion","Soybean","Grapes"],
        "rabi":   ["Wheat","Onion","Tomato","Chickpea"],
        "zaid":   ["Watermelon","Cucumber","Moong"]
    },
    "Nagpur": {
        "kharif": ["Cotton","Soybean","Paddy","Maize","Redgram"],
        "rabi":   ["Wheat","Chickpea","Onion","Orange"],
        "zaid":   ["Watermelon","Moong","Sunflower"]
    },
    "Nashik": {
        "kharif": ["Onion","Tomato","Grapes","Maize","Soybean"],
        "rabi":   ["Onion","Wheat","Chickpea","Tomato"],
        "zaid":   ["Onion","Watermelon","Moong"]
    },
    "Aurangabad": {
        "kharif": ["Cotton","Soybean","Maize","Sugarcane"],
        "rabi":   ["Wheat","Chickpea","Onion","Tomato"],
        "zaid":   ["Watermelon","Moong","Sunflower"]
    },
    "Solapur": {
        "kharif": ["Sugarcane","Cotton","Soybean","Onion"],
        "rabi":   ["Wheat","Onion","Chickpea","Sunflower"],
        "zaid":   ["Onion","Watermelon","Moong"]
    },
    "Kolhapur": {
        "kharif": ["Sugarcane","Soybean","Paddy","Maize"],
        "rabi":   ["Wheat","Onion","Chickpea","Tomato"],
        "zaid":   ["Watermelon","Cucumber","Moong"]
    },
    "Amravati": {
        "kharif": ["Cotton","Soybean","Paddy","Orange","Maize"],
        "rabi":   ["Wheat","Chickpea","Onion","Sunflower"],
        "zaid":   ["Watermelon","Moong","Groundnut"]
    },
    "Sangli": {
        "kharif": ["Sugarcane","Grapes","Soybean","Onion"],
        "rabi":   ["Wheat","Onion","Chickpea","Tomato"],
        "zaid":   ["Onion","Watermelon","Moong"]
    },
    "Latur": {
        "kharif": ["Soybean","Cotton","Tur","Maize","Redgram"],
        "rabi":   ["Wheat","Chickpea","Sunflower","Onion"],
        "zaid":   ["Watermelon","Moong","Groundnut"]
    },

    # ══════════════════════════════════════════
    # KARNATAKA — 10 districts
    # ══════════════════════════════════════════
    "Bengaluru": {
        "kharif": ["Ragi","Maize","Vegetables","Flowers"],
        "rabi":   ["Tomato","Beans","Carrot","Beetroot"],
        "zaid":   ["Cucumber","Watermelon","Leafy Greens"]
    },
    "Mysuru": {
        "kharif": ["Paddy","Maize","Sugarcane","Ragi","Tobacco"],
        "rabi":   ["Wheat","Tomato","Onion","Potato"],
        "zaid":   ["Watermelon","Moong","Groundnut"]
    },
    "Hubli": {
        "kharif": ["Cotton","Soybean","Sunflower","Maize"],
        "rabi":   ["Wheat","Chickpea","Onion","Sunflower"],
        "zaid":   ["Watermelon","Moong","Groundnut"]
    },
    "Mangaluru": {
        "kharif": ["Paddy","Coconut","Arecanut","Banana"],
        "rabi":   ["Vegetables","Banana","Coconut"],
        "zaid":   ["Vegetables","Watermelon","Cucumber"]
    },
    "Belagavi": {
        "kharif": ["Sugarcane","Cotton","Soybean","Maize"],
        "rabi":   ["Wheat","Chickpea","Onion","Potato"],
        "zaid":   ["Watermelon","Moong","Groundnut"]
    },
    "Dharwad": {
        "kharif": ["Cotton","Soybean","Sunflower","Maize"],
        "rabi":   ["Wheat","Chickpea","Onion","Sunflower"],
        "zaid":   ["Watermelon","Moong","Groundnut"]
    },
    "Vijayapura": {
        "kharif": ["Sugarcane","Cotton","Soybean","Sunflower"],
        "rabi":   ["Wheat","Chickpea","Onion","Sunflower"],
        "zaid":   ["Watermelon","Moong","Groundnut"]
    },
    "Davanagere": {
        "kharif": ["Paddy","Maize","Cotton","Sunflower"],
        "rabi":   ["Wheat","Chickpea","Onion","Tomato"],
        "zaid":   ["Watermelon","Moong","Groundnut"]
    },
    "Shimoga": {
        "kharif": ["Paddy","Maize","Sugarcane","Arecanut"],
        "rabi":   ["Vegetables","Tomato","Onion"],
        "zaid":   ["Watermelon","Cucumber","Moong"]
    },
    "Tumkur": {
        "kharif": ["Groundnut","Ragi","Coconut","Mulberry"],
        "rabi":   ["Tomato","Onion","Chilli","Sunflower"],
        "zaid":   ["Groundnut","Watermelon","Moong"]
    },

    # ══════════════════════════════════════════
    # TAMIL NADU — 10 districts
    # ══════════════════════════════════════════
    "Chennai": {
        "kharif": ["Vegetables","Flowers","Leafy Greens"],
        "rabi":   ["Tomato","Leafy Vegetables","Flowers"],
        "zaid":   ["Cucumber","Watermelon","Leafy Greens"]
    },
    "Coimbatore": {
        "kharif": ["Cotton","Maize","Sugarcane","Banana","Turmeric"],
        "rabi":   ["Wheat","Onion","Tomato","Banana"],
        "zaid":   ["Watermelon","Moong","Groundnut"]
    },
    "Madurai": {
        "kharif": ["Paddy","Cotton","Banana","Maize"],
        "rabi":   ["Chilli","Onion","Tomato","Banana"],
        "zaid":   ["Watermelon","Moong","Groundnut"]
    },
    "Salem": {
        "kharif": ["Paddy","Maize","Sugarcane","Mango"],
        "rabi":   ["Tomato","Onion","Chilli","Mango"],
        "zaid":   ["Watermelon","Moong","Mango"]
    },
    "Trichy": {
        "kharif": ["Paddy","Sugarcane","Banana","Maize"],
        "rabi":   ["Paddy","Banana","Onion","Tomato"],
        "zaid":   ["Watermelon","Moong","Banana"]
    },
    "Tirunelveli": {
        "kharif": ["Paddy","Banana","Coconut","Cotton"],
        "rabi":   ["Banana","Coconut","Vegetables"],
        "zaid":   ["Watermelon","Moong","Banana"]
    },
    "Vellore": {
        "kharif": ["Paddy","Groundnut","Mango","Sugarcane"],
        "rabi":   ["Groundnut","Tomato","Onion","Mango"],
        "zaid":   ["Groundnut","Watermelon","Moong"]
    },
    "Erode": {
        "kharif": ["Turmeric","Cotton","Maize","Sugarcane"],
        "rabi":   ["Turmeric","Onion","Tomato","Banana"],
        "zaid":   ["Watermelon","Moong","Groundnut"]
    },
    "Dindigul": {
        "kharif": ["Paddy","Banana","Groundnut","Cotton"],
        "rabi":   ["Banana","Onion","Tomato","Chilli"],
        "zaid":   ["Watermelon","Moong","Groundnut"]
    },
    "Thanjavur": {
        "kharif": ["Paddy","Banana","Sugarcane","Groundnut"],
        "rabi":   ["Paddy","Banana","Onion","Tomato"],
        "zaid":   ["Watermelon","Moong","Banana"]
    },

    # ══════════════════════════════════════════
    # UTTAR PRADESH — 10 districts
    # ══════════════════════════════════════════
    "Lucknow": {
        "kharif": ["Paddy","Maize","Vegetables","Flowers"],
        "rabi":   ["Wheat","Potato","Mustard","Pea"],
        "zaid":   ["Watermelon","Moong","Groundnut"]
    },
    "Kanpur": {
        "kharif": ["Paddy","Maize","Cotton","Groundnut"],
        "rabi":   ["Wheat","Mustard","Potato","Chickpea"],
        "zaid":   ["Watermelon","Moong","Groundnut"]
    },
    "Agra": {
        "kharif": ["Paddy","Maize","Groundnut","Brinjal"],
        "rabi":   ["Wheat","Mustard","Potato","Pea"],
        "zaid":   ["Watermelon","Moong","Cucumber"]
    },
    "Varanasi": {
        "kharif": ["Paddy","Maize","Vegetables","Sugarcane"],
        "rabi":   ["Wheat","Mustard","Potato","Pea"],
        "zaid":   ["Watermelon","Moong","Vegetables"]
    },
    "Allahabad": {
        "kharif": ["Paddy","Maize","Sugarcane","Groundnut"],
        "rabi":   ["Wheat","Mustard","Potato","Chickpea"],
        "zaid":   ["Watermelon","Moong","Groundnut"]
    },
    "Meerut": {
        "kharif": ["Sugarcane","Paddy","Maize","Vegetables"],
        "rabi":   ["Wheat","Mustard","Potato","Pea"],
        "zaid":   ["Watermelon","Moong","Vegetables"]
    },
    "Ghaziabad": {
        "kharif": ["Sugarcane","Paddy","Vegetables","Flowers"],
        "rabi":   ["Wheat","Mustard","Potato","Vegetables"],
        "zaid":   ["Watermelon","Cucumber","Vegetables"]
    },
    "Gorakhpur": {
        "kharif": ["Paddy","Maize","Sugarcane","Redgram"],
        "rabi":   ["Wheat","Mustard","Potato","Pea"],
        "zaid":   ["Watermelon","Moong","Groundnut"]
    },
    "Aligarh": {
        "kharif": ["Paddy","Maize","Groundnut","Cotton"],
        "rabi":   ["Wheat","Mustard","Potato","Barley"],
        "zaid":   ["Watermelon","Moong","Groundnut"]
    },
    "Moradabad": {
        "kharif": ["Sugarcane","Paddy","Maize","Cotton"],
        "rabi":   ["Wheat","Mustard","Potato","Pea"],
        "zaid":   ["Watermelon","Moong","Vegetables"]
    },

    # ══════════════════════════════════════════
    # PUNJAB — 10 districts
    # ══════════════════════════════════════════
    "Ludhiana": {
        "kharif": ["Paddy","Maize","Cotton","Vegetables"],
        "rabi":   ["Wheat","Mustard","Potato","Barley"],
        "zaid":   ["Watermelon","Moong","Sunflower"]
    },
    "Amritsar": {
        "kharif": ["Paddy","Maize","Cotton","Sugarcane"],
        "rabi":   ["Wheat","Mustard","Potato","Barley"],
        "zaid":   ["Watermelon","Moong","Sunflower"]
    },
    "Jalandhar": {
        "kharif": ["Paddy","Maize","Vegetables","Cotton"],
        "rabi":   ["Wheat","Mustard","Potato","Barley"],
        "zaid":   ["Watermelon","Moong","Vegetables"]
    },
    "Patiala": {
        "kharif": ["Paddy","Maize","Cotton","Sugarcane"],
        "rabi":   ["Wheat","Mustard","Potato","Barley"],
        "zaid":   ["Watermelon","Moong","Sunflower"]
    },
    "Bathinda": {
        "kharif": ["Cotton","Paddy","Maize","Groundnut"],
        "rabi":   ["Wheat","Mustard","Chickpea","Barley"],
        "zaid":   ["Watermelon","Moong","Groundnut"]
    },
    "Mohali": {
        "kharif": ["Paddy","Maize","Vegetables","Flowers"],
        "rabi":   ["Wheat","Mustard","Potato","Vegetables"],
        "zaid":   ["Watermelon","Cucumber","Moong"]
    },
    "Pathankot": {
        "kharif": ["Paddy","Maize","Sugarcane","Vegetables"],
        "rabi":   ["Wheat","Mustard","Potato","Barley"],
        "zaid":   ["Watermelon","Moong","Vegetables"]
    },
    "Hoshiarpur": {
        "kharif": ["Paddy","Maize","Sugarcane","Ginger"],
        "rabi":   ["Wheat","Mustard","Potato","Barley"],
        "zaid":   ["Watermelon","Moong","Ginger"]
    },
    "Gurdaspur": {
        "kharif": ["Paddy","Maize","Sugarcane","Cotton"],
        "rabi":   ["Wheat","Mustard","Potato","Barley"],
        "zaid":   ["Watermelon","Moong","Sunflower"]
    },
    "Firozpur": {
        "kharif": ["Cotton","Paddy","Maize","Groundnut"],
        "rabi":   ["Wheat","Mustard","Chickpea","Barley"],
        "zaid":   ["Watermelon","Moong","Groundnut"]
    },

    # ══════════════════════════════════════════
    # RAJASTHAN — 10 districts
    # ══════════════════════════════════════════
    "Jaipur": {
        "kharif": ["Bajra","Maize","Groundnut","Moong","Guar"],
        "rabi":   ["Wheat","Mustard","Chickpea","Barley"],
        "zaid":   ["Watermelon","Moong","Groundnut"]
    },
    "Jodhpur": {
        "kharif": ["Bajra","Moth Bean","Guar","Groundnut"],
        "rabi":   ["Wheat","Mustard","Chickpea","Cumin"],
        "zaid":   ["Watermelon","Moong","Guar"]
    },
    "Udaipur": {
        "kharif": ["Maize","Paddy","Soybean","Bajra"],
        "rabi":   ["Wheat","Mustard","Chickpea","Barley"],
        "zaid":   ["Watermelon","Moong","Groundnut"]
    },
    "Kota": {
        "kharif": ["Soybean","Maize","Cotton","Paddy"],
        "rabi":   ["Wheat","Mustard","Chickpea","Coriander"],
        "zaid":   ["Watermelon","Moong","Groundnut"]
    },
    "Bikaner": {
        "kharif": ["Bajra","Cotton","Guar","Moth Bean"],
        "rabi":   ["Wheat","Mustard","Chickpea","Cumin"],
        "zaid":   ["Watermelon","Moong","Guar"]
    },
    "Ajmer": {
        "kharif": ["Bajra","Maize","Groundnut","Guar"],
        "rabi":   ["Wheat","Mustard","Chickpea","Barley"],
        "zaid":   ["Watermelon","Moong","Groundnut"]
    },
    "Bhilwara": {
        "kharif": ["Maize","Bajra","Soybean","Cotton"],
        "rabi":   ["Wheat","Mustard","Chickpea","Barley"],
        "zaid":   ["Watermelon","Moong","Groundnut"]
    },
    "Alwar": {
        "kharif": ["Bajra","Maize","Groundnut","Cotton"],
        "rabi":   ["Wheat","Mustard","Chickpea","Mustard"],
        "zaid":   ["Watermelon","Moong","Groundnut"]
    },
    "Bharatpur": {
        "kharif": ["Paddy","Maize","Bajra","Groundnut"],
        "rabi":   ["Wheat","Mustard","Potato","Barley"],
        "zaid":   ["Watermelon","Moong","Groundnut"]
    },
    "Sikar": {
        "kharif": ["Bajra","Groundnut","Guar","Maize"],
        "rabi":   ["Wheat","Mustard","Chickpea","Cumin"],
        "zaid":   ["Watermelon","Moong","Groundnut"]
    },

    # ══════════════════════════════════════════
    # MADHYA PRADESH — 10 districts
    # ══════════════════════════════════════════
    "Bhopal": {
        "kharif": ["Soybean","Maize","Paddy","Cotton"],
        "rabi":   ["Wheat","Chickpea","Mustard","Onion"],
        "zaid":   ["Watermelon","Moong","Groundnut"]
    },
    "Indore": {
        "kharif": ["Soybean","Maize","Cotton","Groundnut"],
        "rabi":   ["Wheat","Chickpea","Onion","Garlic"],
        "zaid":   ["Watermelon","Moong","Groundnut"]
    },
    "Gwalior": {
        "kharif": ["Paddy","Maize","Soybean","Cotton"],
        "rabi":   ["Wheat","Mustard","Chickpea","Potato"],
        "zaid":   ["Watermelon","Moong","Groundnut"]
    },
    "Jabalpur": {
        "kharif": ["Paddy","Maize","Soybean","Redgram"],
        "rabi":   ["Wheat","Chickpea","Mustard","Onion"],
        "zaid":   ["Watermelon","Moong","Vegetables"]
    },
    "Ujjain": {
        "kharif": ["Soybean","Maize","Cotton","Groundnut"],
        "rabi":   ["Wheat","Chickpea","Onion","Garlic"],
        "zaid":   ["Watermelon","Moong","Groundnut"]
    },
    "Sagar": {
        "kharif": ["Soybean","Paddy","Maize","Cotton"],
        "rabi":   ["Wheat","Chickpea","Mustard","Onion"],
        "zaid":   ["Watermelon","Moong","Groundnut"]
    },
    "Rewa": {
        "kharif": ["Paddy","Maize","Soybean","Redgram"],
        "rabi":   ["Wheat","Chickpea","Mustard","Potato"],
        "zaid":   ["Watermelon","Moong","Vegetables"]
    },
    "Satna": {
        "kharif": ["Paddy","Maize","Soybean","Redgram"],
        "rabi":   ["Wheat","Chickpea","Mustard","Onion"],
        "zaid":   ["Watermelon","Moong","Groundnut"]
    },
    "Dewas": {
        "kharif": ["Soybean","Maize","Cotton","Onion"],
        "rabi":   ["Wheat","Chickpea","Onion","Garlic"],
        "zaid":   ["Watermelon","Moong","Groundnut"]
    },
    "Chhindwara": {
        "kharif": ["Soybean","Paddy","Maize","Cotton"],
        "rabi":   ["Wheat","Chickpea","Mustard","Onion"],
        "zaid":   ["Watermelon","Moong","Groundnut"]
    },

    # ══════════════════════════════════════════
    # GUJARAT — 10 districts
    # ══════════════════════════════════════════
    "Ahmedabad": {
        "kharif": ["Cotton","Groundnut","Bajra","Castor"],
        "rabi":   ["Wheat","Chickpea","Mustard","Cumin"],
        "zaid":   ["Watermelon","Moong","Groundnut"]
    },
    "Surat": {
        "kharif": ["Sugarcane","Paddy","Cotton","Banana"],
        "rabi":   ["Wheat","Chickpea","Vegetables","Banana"],
        "zaid":   ["Watermelon","Cucumber","Moong"]
    },
    "Vadodara": {
        "kharif": ["Cotton","Paddy","Maize","Sugarcane"],
        "rabi":   ["Wheat","Chickpea","Onion","Mustard"],
        "zaid":   ["Watermelon","Moong","Groundnut"]
    },
    "Rajkot": {
        "kharif": ["Groundnut","Cotton","Bajra","Castor"],
        "rabi":   ["Wheat","Chickpea","Cumin","Mustard"],
        "zaid":   ["Groundnut","Watermelon","Moong"]
    },
    "Bhavnagar": {
        "kharif": ["Groundnut","Cotton","Bajra","Castor"],
        "rabi":   ["Wheat","Chickpea","Cumin","Mustard"],
        "zaid":   ["Groundnut","Watermelon","Moong"]
    },
    "Jamnagar": {
        "kharif": ["Groundnut","Cotton","Bajra","Castor"],
        "rabi":   ["Wheat","Chickpea","Cumin","Mustard"],
        "zaid":   ["Groundnut","Watermelon","Moong"]
    },
    "Gandhinagar": {
        "kharif": ["Cotton","Bajra","Maize","Vegetables"],
        "rabi":   ["Wheat","Chickpea","Mustard","Vegetables"],
        "zaid":   ["Watermelon","Moong","Cucumber"]
    },
    "Anand": {
        "kharif": ["Paddy","Cotton","Banana","Tobacco"],
        "rabi":   ["Wheat","Potato","Onion","Banana"],
        "zaid":   ["Watermelon","Moong","Banana"]
    },
    "Mehsana": {
        "kharif": ["Cotton","Bajra","Maize","Castor"],
        "rabi":   ["Wheat","Chickpea","Cumin","Mustard"],
        "zaid":   ["Watermelon","Moong","Groundnut"]
    },
    "Junagadh": {
        "kharif": ["Groundnut","Cotton","Bajra","Mango"],
        "rabi":   ["Wheat","Chickpea","Cumin","Mustard"],
        "zaid":   ["Groundnut","Mango","Watermelon"]
    },
}

# ─────────────────────────────────────────────────────────────
# STEP 2 — Add crop name translations
# Inside your translate_crop() function, add these to 'hi' and 'te' dicts
# ─────────────────────────────────────────────────────────────

CROP_TRANSLATIONS_HI = {
    # Already in your app
    'Tomato':'टमाटर','Brinjal':'बैंगन','Chilli':'मिर्च','Groundnut':'मूंगफली',
    'Mango':'आम','Papaya':'पपीता','Guava':'अमरूद','Marigold':'गेंदा','Rose':'गुलाब',
    'Aloe Vera':'एलोवेरा','Onion':'प्याज','Garlic':'लहसुन','Soybean':'सोयाबीन',
    'Banana':'केला','Orange':'संतरा','Jasmine':'चमेली','Rice':'चावल','Sugarcane':'गन्ना',
    'Maize':'मक्का','Mustard':'सरसों','Litchi':'लीची','Wheat':'गेहूं','Carrot':'गाजर',
    'Watermelon':'तरबूज','Cotton':'कपास','Jute':'जूट','Millet':'बाजरा',

    # NEW crops from DISTRICT_CROPS
    'Paddy'      : 'धान',
    'Redgram'    : 'अरहर दाल',
    'Chickpea'   : 'चना',
    'Sunflower'  : 'सूरजमुखी',
    'Safflower'  : 'कुसुम',
    'Moong'      : 'मूंग',
    'Sesame'     : 'तिल',
    'Turmeric'   : 'हल्दी',
    'Tobacco'    : 'तंबाकू',
    'Cashew'     : 'काजू',
    'Ragi'       : 'रागी',
    'Bajra'      : 'बाजरा',
    'Jowar'      : 'ज्वार',
    'Horsegram'  : 'कुलथी',
    'Guar'       : 'ग्वार',
    'Moth Bean'  : 'मोठ',
    'Cumin'      : 'जीरा',
    'Coriander'  : 'धनिया',
    'Barley'     : 'जौ',
    'Potato'     : 'आलू',
    'Pea'        : 'मटर',
    'Castor'     : 'अरंडी',
    'Arecanut'   : 'सुपारी',
    'Coconut'    : 'नारियल',
    'Grapes'     : 'अंगूर',
    'Ginger'     : 'अदरक',
    'Tur'        : 'तुअर',
    'Flowers'    : 'फूल',
    'Vegetables' : 'सब्जियां',
    'Leafy Greens'     : 'हरी पत्तेदार सब्जियां',
    'Leafy Vegetables' : 'पत्तेदार सब्जियां',
}

CROP_TRANSLATIONS_TE = {
    # Already in your app
    'Tomato':'టమాటా','Brinjal':'వంకాయ','Chilli':'మిర్చి','Groundnut':'వేరుశెనగ',
    'Mango':'మామిడి','Papaya':'బొప్పాయి','Guava':'జామ','Marigold':'చేమంతి','Rose':'గులాబి',
    'Aloe Vera':'అలోవెరా','Onion':'ఉల్లి','Garlic':'వెల్లుల్లి','Soybean':'సోయాబీన్',
    'Banana':'అరటి','Orange':'నారింజ','Jasmine':'మల్లె','Rice':'వరి','Sugarcane':'చెరకు',
    'Maize':'మొక్కజొన్న','Mustard':'ఆవాలు','Litchi':'లీచీ','Wheat':'గోధుమ','Carrot':'క్యారెట్',
    'Watermelon':'పుచ్చకాయ','Cotton':'పత్తి','Jute':'జనపనార','Millet':'జొన్న',

    # NEW crops from DISTRICT_CROPS
    'Paddy'      : 'వరి',
    'Redgram'    : 'కందులు',
    'Chickpea'   : 'శనగలు',
    'Sunflower'  : 'పొద్దుతిరుగుడు',
    'Safflower'  : 'కుసుమ',
    'Moong'      : 'పెసలు',
    'Sesame'     : 'నువ్వులు',
    'Turmeric'   : 'పసుపు',
    'Tobacco'    : 'పొగాకు',
    'Cashew'     : 'జీడిపప్పు',
    'Ragi'       : 'రాగి',
    'Bajra'      : 'సజ్జలు',
    'Jowar'      : 'జొన్న',
    'Horsegram'  : 'అలసంద',
    'Guar'       : 'గోరుచిక్కుడు',
    'Moth Bean'  : 'మోత్ బీన్',
    'Cumin'      : 'జీలకర్ర',
    'Coriander'  : 'కొత్తిమీర',
    'Barley'     : 'బార్లీ',
    'Potato'     : 'బంగాళాదుంప',
    'Pea'        : 'బఠాణీ',
    'Castor'     : 'ఆముదం',
    'Arecanut'   : 'వక్కపోక',
    'Coconut'    : 'కొబ్బరి',
    'Grapes'     : 'ద్రాక్ష',
    'Ginger'     : 'అల్లం',
    'Tur'        : 'కందులు',
    'Flowers'    : 'పూలు',
    'Vegetables' : 'కూరగాయలు',
    'Leafy Greens'     : 'ఆకు కూరలు',
    'Leafy Vegetables' : 'ఆకు కూరలు',
}


DISEASES = {
    "Tomato Late Blight": {
        "cause": {"en":"Fungal - Phytophthora infestans","hi":"फंगल - फाइटोफ्थोरा इन्फेस्टान्स","te":"శిలీంధ్ర - ఫైటోఫ్తోరా ఇన్ఫెస్టాన్స్"},
        "treatment": {
            "en": "Apply Copper Fungicide (Bordeaux mixture) every 7 days. Remove and destroy infected leaves immediately. Ensure good air circulation.",
            "hi": "हर 7 दिनों में कॉपर फंगीसाइड लगाएं। संक्रमित पत्तियों को तुरंत हटाएं और नष्ट करें।",
            "te": "ప్రతి 7 రోజులకు కాపర్ ఫంగీసైడ్ వేయండి. సోకిన ఆకులను వెంటనే తొలగించి నాశనం చేయండి."
        },
        "organic": {"en":"Neem oil spray (5ml per litre water) every 5 days. Garlic extract spray also effective.","hi":"हर 5 दिनों में नीम तेल स्प्रे (5ml/लीटर पानी)। लहसुन अर्क स्प्रे भी प्रभावी।","te":"ప్రతి 5 రోజులకు వేప నూనె స్ప్రే (5ml/లీటర్ నీరు). వెల్లుల్లి అర్క స్ప్రే కూడా ప్రభావవంతం."},
        "prevention": {"en":"Avoid overwatering, improve drainage, rotate crops annually, use resistant varieties.","hi":"अत्यधिक सिंचाई से बचें, जल निकासी सुधारें, वार्षिक फसल चक्र अपनाएं।","te":"అధిక నీటిని నివారించండి, నీటి పారుదల మెరుగుపరచండి, వార్షిక పంట మార్పిడి చేయండి."},
        "confidence": 94, "severity": "Moderate",
        "affected_crops": ["Tomato","Potato","Pepper","Eggplant","Tomatillo"],
        "treatment_cost": {"min": 800, "max": 1500, "unit": "per acre"},
        "spray_schedule": [
            {"day":{"en":"Day 1","hi":"दिन 1","te":"రోజు 1"},"action":{"en":"Remove all infected leaves and stems","hi":"सभी संक्रमित पत्तियाँ और तने हटाएं","te":"అన్ని సోకిన ఆకులు మరియు కాండాలు తీసివేయండి"},"product":"Manual removal","time":{"en":"Morning","hi":"सुबह","te":"ఉదయం"}},
            {"day":{"en":"Day 1","hi":"दिन 1","te":"రోజు 1"},"action":{"en":"Apply Copper Fungicide (Bordeaux mixture)","hi":"कॉपर फंगीसाइड (बोर्डो मिश्रण) लगाएं","te":"కాపర్ ఫంగీసైడ్ (బోర్డో మిశ్రమం) వేయండి"},"product":"Copper oxychloride 50% WP @ 3g/L","time":{"en":"Evening","hi":"शाम","te":"సాయంత్రం"}},
            {"day":{"en":"Day 4","hi":"दिन 4","te":"రోజు 4"},"action":{"en":"Second spray — Mancozeb solution","hi":"दूसरा स्प्रे — मेन्कोजेब घोल","te":"రెండవ స్ప్రే — మాంకోజెబ్ ద్రావణం"},"product":"Mancozeb 75% WP @ 2g/L","time":{"en":"Morning","hi":"सुबह","te":"ఉదయం"}},
            {"day":{"en":"Day 7","hi":"दिन 7","te":"రోజు 7"},"action":{"en":"Third spray — repeat Copper Fungicide","hi":"तीसरा स्प्रे — कॉपर फंगीसाइड दोबारा","te":"మూడవ స్ప్రే — కాపర్ ఫంగీసైడ్ మళ్ళీ"},"product":"Copper oxychloride 50% WP @ 3g/L","time":{"en":"Evening","hi":"शाम","te":"సాయంత్రం"}},
            {"day":{"en":"Day 10","hi":"दिन 10","te":"రోజు 10"},"action":{"en":"Inspect — if spreading apply Ridomil Gold","hi":"निरीक्षण — यदि फैल रहा है तो रिडोमिल गोल्ड लगाएं","te":"తనిఖీ — వ్యాప్తి చెందితే రిడోమిల్ గోల్డ్ వేయండి"},"product":"Metalaxyl 8% + Mancozeb 64%","time":{"en":"Morning","hi":"सुबह","te":"ఉదయం"}},
            {"day":{"en":"Day 14","hi":"दिन 14","te":"రోజు 14"},"action":{"en":"Final preventive spray + field inspection","hi":"अंतिम निवारक स्प्रे + खेत निरीक्षण","te":"చివరి నివారణ స్ప్రే + పొలం తనిఖీ"},"product":"Neem oil 5ml/L (organic)","time":{"en":"Evening","hi":"शाम","te":"సాయంత్రం"}},
        ]
    },
    "Rice Blast": {
        "cause": {"en":"Fungal - Magnaporthe oryzae","hi":"फंगल - मैग्नापोर्थे ओरिजे","te":"శిలీంధ్ర - మాగ్నపోర్తే ఒరైజే"},
        "treatment": {
            "en": "Apply Tricyclazole 75% WP @ 0.6g/litre water. Drain field water for 3-4 days. Spray in early morning.",
            "hi": "ट्राइसाइक्लाज़ोल 75% WP @ 0.6g/लीटर लगाएं। 3-4 दिनों के लिए खेत से पानी निकालें।",
            "te": "ట్రైసైక్లజోల్ 75% WP @ 0.6g/లీటర్ వేయండి. 3-4 రోజులు పొలం నుండి నీరు తీసివేయండి."
        },
        "organic": {"en":"Silicon-based spray, Trichoderma viride bio-fungicide @ 5g/litre.","hi":"सिलिकॉन-आधारित स्प्रे, ट्राइकोडर्मा विराइड @ 5g/लीटर।","te":"సిలికాన్-ఆధారిత స్ప్రే, ట్రైకోడర్మా విరైడ్ @ 5g/లీటర్."},
        "prevention": {"en":"Avoid excess nitrogen, maintain proper plant spacing, use certified seeds.","hi":"अत्यधिक नाइट्रोजन से बचें, उचित दूरी बनाए रखें, प्रमाणित बीज उपयोग करें।","te":"అదనపు నత్రజనిని నివారించండి, సరైన మొక్కల మధ్య దూరం పాటించండి."},
        "confidence": 91, "severity": "Severe",
        "affected_crops": ["Rice","Wheat","Barley","Finger Millet","Foxtail Millet"],
        "treatment_cost": {"min": 1200, "max": 2200, "unit": "per acre"},
        "spray_schedule": [
            {"day":{"en":"Day 1","hi":"दिन 1","te":"రోజు 1"},"action":{"en":"Drain field water completely","hi":"खेत का पानी पूरी तरह निकालें","te":"పొలం నీటిని పూర్తిగా తీసివేయండి"},"product":"No spray — field management","time":{"en":"Morning","hi":"सुबह","te":"ఉదయం"}},
            {"day":{"en":"Day 2","hi":"दिन 2","te":"రోజు 2"},"action":{"en":"Apply Tricyclazole fungicide","hi":"ट्राइसाइक्लाज़ोल फफूंदनाशक लगाएं","te":"ట్రైసైక్లజోల్ ఫంగిసైడ్ వేయండి"},"product":"Tricyclazole 75% WP @ 0.6g/L","time":{"en":"Early Morning","hi":"सुबह जल्दी","te":"తెల్లవారుజామున"}},
            {"day":{"en":"Day 5","hi":"दिन 5","te":"రోజు 5"},"action":{"en":"Re-flood field to 3cm depth","hi":"खेत में 3cm गहराई तक पानी भरें","te":"పొలాన్ని 3cm లోతు వరకు నీరు నింపండి"},"product":"Field water management","time":{"en":"Morning","hi":"सुबह","te":"ఉదయం"}},
            {"day":{"en":"Day 7","hi":"दिन 7","te":"రోజు 7"},"action":{"en":"Second spray — Isoprothiolane","hi":"दूसरा स्प्रे — आइसोप्रोथियोलेन","te":"రెండవ స్ప్రే — ఐసోప్రొతయోలేన్"},"product":"Isoprothiolane 40% EC @ 1.5ml/L","time":{"en":"Early Morning","hi":"सुबह जल्दी","te":"తెల్లవారుజామున"}},
            {"day":{"en":"Day 12","hi":"दिन 12","te":"రోజు 12"},"action":{"en":"Bio-fungicide application","hi":"जैव फफूंदनाशक प्रयोग","te":"జీవ శిలీంధ్రనాశిని వేయండి"},"product":"Trichoderma viride @ 5g/L","time":{"en":"Evening","hi":"शाम","te":"సాయంత్రం"}},
            {"day":{"en":"Day 15","hi":"दिन 15","te":"రోజు 15"},"action":{"en":"Final inspection + preventive spray","hi":"अंतिम निरीक्षण + निवारक स्प्रे","te":"చివరి తనిఖీ + నివారణ స్ప్రే"},"product":"Propiconazole 25% EC @ 1ml/L","time":{"en":"Morning","hi":"सुबह","te":"ఉదయం"}},
        ]
    },
    "Powdery Mildew": {
        "cause": {"en":"Fungal - Erysiphe cichoracearum","hi":"फंगल - एरिसिफे सिकोरेसेरम","te":"శిలీంధ్ర - ఎరిసిఫే సిక్కోరేసెరమ్"},
        "treatment": {
            "en": "Apply Sulphur 80% WP @ 2g/litre water. Spray Wettable Sulphur 0.2% solution. Remove badly infected plant parts.",
            "hi": "सल्फर 80% WP @ 2g/लीटर पानी लगाएं। वेटेबल सल्फर 0.2% घोल स्प्रे करें।",
            "te": "సల్ఫర్ 80% WP @ 2g/లీటర్ నీటిలో వేయండి. వెట్టబుల్ సల్ఫర్ 0.2% ద్రావణం పిచికారీ చేయండి."
        },
        "organic": {"en":"Baking soda spray (1 tbsp per litre water) weekly. Diluted milk spray (1:9 ratio).","hi":"बेकिंग सोडा स्प्रे (1 tbsp/लीटर पानी) साप्ताहिक। पतला दूध स्प्रे (1:9 अनुपात)।","te":"వారానికోసారి బేకింగ్ సోడా స్ప్రే (1 tbsp/లీటర్). పలుచన పాల స్ప్రే (1:9)."},
        "prevention": {"en":"Ensure good air circulation, avoid overhead watering, plant resistant varieties.","hi":"अच्छी वायु संचार सुनिश्चित करें, ऊपर से सिंचाई से बचें, प्रतिरोधी किस्में लगाएं।","te":"మంచి గాలి ప్రసరణ నిర్ధారించండి, పై నుండి నీటి తడుపడం నివారించండి."},
        "confidence": 88, "severity": "Mild",
        "affected_crops": ["Wheat","Cucumber","Mango","Grape","Pea","Rose","Gourd"],
        "treatment_cost": {"min": 400, "max": 900, "unit": "per acre"},
        "spray_schedule": [
            {"day":{"en":"Day 1","hi":"दिन 1","te":"రోజు 1"},"action":{"en":"Prune heavily infected leaves/branches","hi":"भारी संक्रमित पत्तियाँ/शाखाएं काटें","te":"తీవ్రంగా సోకిన ఆకులు/కొమ్మలు కత్తిరించండి"},"product":"Manual pruning","time":{"en":"Morning","hi":"सुबह","te":"ఉదయం"}},
            {"day":{"en":"Day 1","hi":"दिन 1","te":"రోజు 1"},"action":{"en":"Apply Wettable Sulphur spray","hi":"वेटेबल सल्फर स्प्रे लगाएं","te":"వెట్టబుల్ సల్ఫర్ స్ప్రే వేయండి"},"product":"Sulphur 80% WP @ 2g/L","time":{"en":"Evening","hi":"शाम","te":"సాయంత్రం"}},
            {"day":{"en":"Day 5","hi":"दिन 5","te":"రోజు 5"},"action":{"en":"Baking soda organic spray","hi":"बेकिंग सोडा जैविक स्प्रे","te":"బేకింగ్ సోడా సేంద్రీయ స్ప్రే"},"product":"Baking soda 1 tbsp/L + soap","time":{"en":"Morning","hi":"सुबह","te":"ఉదయం"}},
            {"day":{"en":"Day 8","hi":"दिन 8","te":"రోజు 8"},"action":{"en":"Second chemical spray","hi":"दूसरा रासायनिक स्प्रे","te":"రెండవ రసాయన స్ప్రే"},"product":"Hexaconazole 5% EC @ 2ml/L","time":{"en":"Evening","hi":"शाम","te":"సాయంత్రం"}},
            {"day":{"en":"Day 12","hi":"दिन 12","te":"రోజు 12"},"action":{"en":"Milk spray (organic option)","hi":"दूध स्प्रे (जैविक विकल्प)","te":"పాల స్ప్రే (సేంద్రీయ వికల్పం)"},"product":"Diluted milk 1:9 ratio","time":{"en":"Morning","hi":"सुबह","te":"ఉదయం"}},
            {"day":{"en":"Day 15","hi":"दिन 15","te":"రోజు 15"},"action":{"en":"Final preventive sulphur spray","hi":"अंतिम निवारक सल्फर स्प्रे","te":"చివరి నివారణ సల్ఫర్ స్ప్రే"},"product":"Sulphur 80% WP @ 2g/L","time":{"en":"Evening","hi":"शाम","te":"సాయంత్రం"}},
        ]
    },
    "Leaf Rust": {
        "cause": {"en":"Fungal - Puccinia species","hi":"फंगल - पुक्किनिया प्रजाति","te":"శిలీంధ్ర - పక్కినియా జాతి"},
        "treatment": {
            "en": "Apply Mancozeb 75% WP @ 2g/litre or Propiconazole 25% EC @ 1ml/litre. Start treatment at first sign.",
            "hi": "मैन्कोजेब 75% WP @ 2g/लीटर या प्रोपिकोनाज़ोल @ 1ml/लीटर लगाएं। पहले संकेत पर उपचार शुरू करें।",
            "te": "మాంకోజెబ్ 75% WP @ 2g/లీటర్ లేదా ప్రొపికోనజోల్ @ 1ml/లీటర్ వేయండి."
        },
        "organic": {"en":"Garlic extract spray, Compost tea application weekly.","hi":"लहसुन अर्क स्प्रे, साप्ताहिक खाद की चाय।","te":"వెల్లుల్లి అర్క స్ప్రే, వారానికోసారి కంపోస్ట్ టీ."},
        "prevention": {"en":"Use rust-resistant varieties, remove crop debris after harvest, avoid dense planting.","hi":"जंग-प्रतिरोधी किस्में उपयोग करें, कटाई के बाद फसल अवशेष हटाएं।","te":"తుప్పు-నిరోధక రకాలు ఉపయోగించండి, కోత తర్వాత పంట అవశేషాలు తీసివేయండి."},
        "confidence": 86, "severity": "Moderate",
        "affected_crops": ["Wheat","Barley","Coffee","Groundnut","Soybean","Bean"],
        "treatment_cost": {"min": 600, "max": 1200, "unit": "per acre"},
        "spray_schedule": [
            {"day":{"en":"Day 1","hi":"दिन 1","te":"రోజు 1"},"action":{"en":"Remove and burn all infected leaves","hi":"सभी संक्रमित पत्तियाँ हटाएं और जलाएं","te":"అన్ని సోకిన ఆకులు తీసివేసి కాల్చండి"},"product":"Manual removal + burn","time":{"en":"Morning","hi":"सुबह","te":"ఉదయం"}},
            {"day":{"en":"Day 1","hi":"दिन 1","te":"రోజు 1"},"action":{"en":"First Mancozeb spray","hi":"पहला मैन्कोजेब स्प्रे","te":"మొదటి మాంకోజెబ్ స్ప్రే"},"product":"Mancozeb 75% WP @ 2g/L","time":{"en":"Evening","hi":"शाम","te":"సాయంత్రం"}},
            {"day":{"en":"Day 5","hi":"दिन 5","te":"రోజు 5"},"action":{"en":"Garlic extract organic spray","hi":"लहसुन अर्क जैविक स्प्रे","te":"వెల్లుల్లి అర్క సేంద్రీయ స్ప్రే"},"product":"Garlic extract 10ml/L","time":{"en":"Morning","hi":"सुबह","te":"ఉదయం"}},
            {"day":{"en":"Day 7","hi":"दिन 7","te":"రోజు 7"},"action":{"en":"Propiconazole systemic fungicide","hi":"प्रोपिकोनाज़ोल प्रणालीगत फफूंदनाशक","te":"ప్రొపికోనజోల్ వ్యవస్థాగత శిలీంధ్రనాశిని"},"product":"Propiconazole 25% EC @ 1ml/L","time":{"en":"Morning","hi":"सुबह","te":"ఉదయం"}},
            {"day":{"en":"Day 10","hi":"दिन 10","te":"రోజు 10"},"action":{"en":"Compost tea foliar spray","hi":"खाद की चाय पत्ती स्प्रे","te":"కంపోస్ట్ టీ ఆకు స్ప్రే"},"product":"Compost tea 1:10 dilution","time":{"en":"Evening","hi":"शाम","te":"సాయంత్రం"}},
            {"day":{"en":"Day 14","hi":"दिन 14","te":"రోజు 14"},"action":{"en":"Final Mancozeb preventive spray","hi":"अंतिम मैन्कोजेब निवारक स्प्रे","te":"చివరి మాంకోజెబ్ నివారణ స్ప్రే"},"product":"Mancozeb 75% WP @ 2g/L","time":{"en":"Morning","hi":"सुबह","te":"ఉదయం"}},
        ]
    },
    "Bacterial Wilt": {
        "cause": {"en":"Bacterial - Ralstonia solanacearum","hi":"बैक्टीरियल - रालस्टोनिया सोलानेसेरम","te":"బాక్టీరియల్ - రాల్స్టోనియా సోలానేసేరమ్"},
        "treatment": {
            "en": "No effective chemical cure. Remove and destroy infected plants immediately. Apply Bleaching powder @ 10kg/acre to soil.",
            "hi": "कोई प्रभावी रासायनिक उपचार नहीं। संक्रमित पौधों को तुरंत हटाएं। ब्लीचिंग पाउडर @ 10kg/एकड़ लगाएं।",
            "te": "ప్రభావవంతమైన రసాయన చికిత్స లేదు. సోకిన మొక్కలను వెంటనే తొలగించండి. బ్లీచింగ్ పౌడర్ @ 10kg/ఎకరా వేయండి."
        },
        "organic": {"en":"Trichoderma harzianum soil treatment @ 2.5kg/acre. Pseudomonas fluorescens spray.","hi":"ट्राइकोडर्मा हारजियानम मिट्टी उपचार @ 2.5kg/एकड़। स्यूडोमोनास फ्लोरेसेंस स्प्रे।","te":"ట్రైకోడర్మా హార్జియానమ్ మట్టి చికిత్స @ 2.5kg/ఎకరా. స్యూడోమోనాస్ ఫ్లోరెసెన్స్ స్ప్రే."},
        "prevention": {"en":"Crop rotation every 3 years, avoid waterlogging, use disease-free certified seeds.","hi":"हर 3 साल में फसल चक्र, जलजमाव से बचें, रोगमुक्त प्रमाणित बीज उपयोग करें।","te":"ప్రతి 3 సంవత్సరాలకు పంట మార్పిడి, నీటి నిలకడను నివారించండి."},
        "confidence": 89, "severity": "Severe",
        "affected_crops": ["Tomato","Potato","Brinjal","Pepper","Banana","Ginger"],
        "treatment_cost": {"min": 1500, "max": 3000, "unit": "per acre"},
        "spray_schedule": [
            {"day":{"en":"Day 1","hi":"दिन 1","te":"రోజు 1"},"action":{"en":"Remove ALL infected plants from field","hi":"खेत से सभी संक्रमित पौधे हटाएं","te":"పొలం నుండి అన్ని సోకిన మొక్కలు తీసివేయండి"},"product":{"en":"Manual removal — burn plants","hi":"हाथ से हटाएं — पौधे जलाएं","te":"చేతితో తీసివేయండి — మొక్కలు కాల్చండి"},"time":{"en":"Morning","hi":"सुबह","te":"ఉదయం"}},
            {"day":{"en":"Day 2","hi":"दिन 2","te":"రోజు 2"},"action":{"en":"Apply Bleaching powder to infected soil","hi":"संक्रमित मिट्टी पर ब्लीचिंग पाउडर डालें","te":"సోకిన మట్టికి బ్లీచింగ్ పౌడర్ వేయండి"},"product":{"en":"Bleaching powder 10kg/acre","hi":"ब्लीचिंग पाउडर 10kg/एकड़","te":"బ్లీచింగ్ పౌడర్ 10kg/ఎకరా"},"time":{"en":"Afternoon","hi":"दोपहर","te":"మధ్యాహ్నం"}},
            {"day":{"en":"Day 3","hi":"दिन 3","te":"రోజు 3"},"action":{"en":"Soil drench with bio-agent","hi":"जैव-एजेंट से मिट्टी उपचार","te":"జీవ-కారకంతో మట్టి చికిత్స"},"product":{"en":"Trichoderma harzianum 2.5kg/acre","hi":"ट्राइकोडर्मा हारजियानम 2.5kg/एकड़","te":"ట్రైకోడర్మా హార్జియానమ్ 2.5kg/ఎకరా"},"time":{"en":"Morning","hi":"सुबह","te":"ఉదయం"}},
            {"day":{"en":"Day 7","hi":"दिन 7","te":"రోజు 7"},"action":{"en":"Pseudomonas fluorescens soil treatment","hi":"स्यूडोमोनास फ्लोरेसेंस मिट्टी उपचार","te":"స్యూడోమోనాస్ ఫ్లోరెసెన్స్ మట్టి చికిత్స"},"product":{"en":"P. fluorescens 2.5kg/acre","hi":"P. फ्लोरेसेंस 2.5kg/एकड़","te":"P. ఫ్లోరెసెన్స్ 2.5kg/ఎకరా"},"time":{"en":"Morning","hi":"सुबह","te":"ఉదయం"}},
            {"day":{"en":"Day 14","hi":"दिन 14","te":"రోజు 14"},"action":{"en":"Second Trichoderma application","hi":"दूसरा ट्राइकोडर्मा प्रयोग","te":"రెండవ ట్రైకోడర్మా వేయడం"},"product":{"en":"Trichoderma harzianum 2.5kg/acre","hi":"ट्राइकोडर्मा हारजियानम 2.5kg/एकड़","te":"ట్రైకోడర్మా హార్జియానమ్ 2.5kg/ఎకరా"},"time":{"en":"Morning","hi":"सुबह","te":"ఉదయం"}},
            {"day":{"en":"Day 21","hi":"दिन 21","te":"రోజు 21"},"action":{"en":"Field inspection — avoid replanting for 30 days","hi":"खेत निरीक्षण — 30 दिनों तक दोबारा रोपाई न करें","te":"పొలం తనిఖీ — 30 రోజులు మళ్ళీ నాటవద్దు"},"product":{"en":"Observation only","hi":"केवल निरीक्षण","te":"పరిశీలన మాత్రమే"},"time":{"en":"Morning","hi":"सुबह","te":"ఉదయం"}},
        ]
    },
    "Yellow Mosaic Virus": {
        "cause": {"en":"Viral - Begomovirus (spread by whitefly)","hi":"वायरल - बेगोमोवायरस (सफेद मक्खी द्वारा फैलता है)","te":"వైరల్ - బెగోమోవైరస్ (తెల్ల దోమ ద్వారా వ్యాప్తి)"},
        "treatment": {
            "en": "No direct cure for virus. Control whitefly vector using Imidacloprid 17.8 SL @ 0.5ml/litre. Remove infected plants.",
            "hi": "वायरस का कोई सीधा इलाज नहीं। इमिडाक्लोप्रिड से सफेद मक्खी नियंत्रित करें। संक्रमित पौधे हटाएं।",
            "te": "వైరస్‌కు నేరుగా నివారణ లేదు. ఇమిడాక్లోప్రిడ్ తో తెల్ల దోమను నియంత్రించండి. సోకిన మొక్కలు తీసివేయండి."
        },
        "organic": {"en":"Yellow sticky traps to catch whiteflies. Neem oil spray to repel insects.","hi":"सफेद मक्खियाँ पकड़ने के लिए पीले चिपचिपे जाल। नीम तेल स्प्रे।","te":"తెల్ల దోమలు పట్టుకోవడానికి పసుపు అంటే తుంపర. వేప నూనె స్ప్రే."},
        "prevention": {"en":"Use virus-resistant varieties, control whitefly population early, remove infected plants promptly.","hi":"वायरस-प्रतिरोधी किस्में उपयोग करें, सफेद मक्खी को जल्दी नियंत्रित करें।","te":"వైరస్-నిరోధక రకాలు ఉపయోగించండి, తెల్ల దోమ జనాభాను ముందుగా నియంత్రించండి."},
        "confidence": 85, "severity": "Severe",
        "affected_crops": ["Soybean","Mung Bean","Black Gram","Bitter Gourd","Okra","Chilli"],
        "treatment_cost": {"min": 1000, "max": 2000, "unit": "per acre"},
        "spray_schedule": [
            {"day":{"en":"Day 1","hi":"दिन 1","te":"రోజు 1"},"action":{"en":"Install yellow sticky traps across field","hi":"खेत में पीले चिपचिपे जाल लगाएं","te":"పొలం అంతటా పసుపు అంటే తుంపర ఏర్పాటు చేయండి"},"product":{"en":"Yellow sticky traps 10/acre","hi":"पीले चिपचिपे जाल 10/एकड़","te":"పసుపు అంటే తుంపర 10/ఎకరా"},"time":{"en":"Morning","hi":"सुबह","te":"ఉదయం"}},
            {"day":{"en":"Day 1","hi":"दिन 1","te":"రోజు 1"},"action":{"en":"Remove infected plants immediately","hi":"संक्रमित पौधों को तुरंत हटाएं","te":"సోకిన మొక్కలను వెంటనే తీసివేయండి"},"product":{"en":"Manual removal + burn","hi":"हाथ से हटाएं + जलाएं","te":"చేతితో తీసివేయండి + కాల్చండి"},"time":{"en":"Morning","hi":"सुबह","te":"ఉదయం"}},
            {"day":{"en":"Day 2","hi":"दिन 2","te":"రోజు 2"},"action":{"en":"Spray Imidacloprid to kill whiteflies","hi":"इमिडाक्लोप्रिड स्प्रे कर सफेद मक्खी मारें","te":"తెల్ల దోమలను చంపడానికి ఇమిడాక్లోప్రిడ్ స్ప్రే చేయండి"},"product":"Imidacloprid 17.8 SL @ 0.5ml/L","time":{"en":"Evening","hi":"शाम","te":"సాయంత్రం"}},
            {"day":{"en":"Day 5","hi":"दिन 5","te":"రోజు 5"},"action":{"en":"Neem oil spray — repels whiteflies","hi":"नीम तेल स्प्रे — सफेद मक्खियाँ भगाता है","te":"వేప నూనె స్ప్రే — తెల్ల దోమలను వెళ్ళగొడుతుంది"},"product":"Neem oil 5ml/L","time":{"en":"Evening","hi":"शाम","te":"సాయంత్రం"}},
            {"day":{"en":"Day 8","hi":"दिन 8","te":"రోజు 8"},"action":{"en":"Second Imidacloprid spray","hi":"दूसरा इमिडाक्लोप्रिड स्प्रे","te":"రెండవ ఇమిడాక్లోప్రిడ్ స్ప్రే"},"product":"Imidacloprid 17.8 SL @ 0.5ml/L","time":{"en":"Evening","hi":"शाम","te":"సాయంత్రం"}},
            {"day":{"en":"Day 12","hi":"दिन 12","te":"రోజు 12"},"action":{"en":"Check traps, replace if full. Final spray","hi":"जाल जांचें, भरे होने पर बदलें। अंतिम स्प्रे","te":"తుంపర తనిఖీ చేయండి, నిండి ఉంటే మార్చండి. చివరి స్ప్రే"},"product":"Thiamethoxam 25% WG @ 0.3g/L","time":{"en":"Evening","hi":"शाम","te":"సాయంత్రం"}},
        ]
    }
}

QUICK_TIPS = {
    'en': ["💧 Water crops in early morning to reduce evaporation and prevent fungal diseases.",
           "🌱 Add compost to improve soil fertility naturally and reduce chemical fertilizer use.",
           "🦟 Use neem oil spray as an organic pest repellent — safe for humans and environment.",
           "📱 Take weekly photos of your crops to track growth and detect problems early.",
           "🌡️ Always check weather forecasts before applying pesticides for best effectiveness.",
           "🔄 Rotate crops every season to prevent soil depletion and reduce pest buildup.",
           "💊 Apply fertilizers in split doses — not all at once — for better nutrient absorption."],
    'hi': ["💧 वाष्पीकरण कम करने के लिए सुबह जल्दी फसलों को पानी दें।",
           "🌱 मिट्टी की उर्वरता सुधारने के लिए जैविक खाद डालें।",
           "🦟 नीम तेल स्प्रे जैविक कीट विकर्षक के रूप में उपयोग करें।",
           "📱 समस्याओं का जल्द पता लगाने के लिए साप्ताहिक फसल तस्वीरें लें।",
           "🔄 मिट्टी की कमी रोकने के लिए हर सीजन फसल चक्र अपनाएं।"],
    'te': ["💧 బాష్పీభవనం తగ్గించడానికి ఉదయాన్నే పంటలకు నీరు పెట్టండి.",
           "🌱 మట్టి సారతను మెరుగుపరచడానికి కంపోస్ట్ జోడించండి.",
           "🦟 సేంద్రీయ పురుగు నివారకంగా వేప నూనె స్ప్రే వాడండి.",
           "📱 పెరుగుదలను ట్రాక్ చేయడానికి వారానికోసారి పంట ఫోటోలు తీయండి.",
           "🔄 మట్టి క్షీణత నివారించడానికి ప్రతి సీజన్ పంట మార్పిడి చేయండి."]
}


# ─────────────────────────────────────────────
# ADVANCED CROP IDEAS DATA
# ─────────────────────────────────────────────

CROP_DETAILS = {
    "Tomato":     {"cost":15000,"yield_ton":8,"price":25,"water":"Medium","risk":35,"season":["kharif","zaid"],"drought_ok":False},
    "Brinjal":    {"cost":10000,"yield_ton":6,"price":18,"water":"Medium","risk":25,"season":["kharif","rabi"],"drought_ok":False},
    "Chilli":     {"cost":12000,"yield_ton":3,"price":40,"water":"Medium","risk":30,"season":["kharif","rabi"],"drought_ok":False},
    "Groundnut":  {"cost":18000,"yield_ton":2,"price":55,"water":"Low","risk":20,"season":["kharif","zaid"],"drought_ok":True},
    "Mango":      {"cost":20000,"yield_ton":5,"price":60,"water":"Low","risk":15,"season":["rabi"],"drought_ok":True},
    "Papaya":     {"cost":12000,"yield_ton":20,"price":22,"water":"Medium","risk":30,"season":["kharif","zaid"],"drought_ok":False},
    "Guava":      {"cost":15000,"yield_ton":8,"price":30,"water":"Low","risk":20,"season":["rabi","zaid"],"drought_ok":True},
    "Marigold":   {"cost":8000,"yield_ton":4,"price":20,"water":"Low","risk":15,"season":["rabi","kharif"],"drought_ok":True},
    "Rose":       {"cost":25000,"yield_ton":3,"price":80,"water":"Medium","risk":40,"season":["rabi"],"drought_ok":False},
    "Aloe Vera":  {"cost":5000,"yield_ton":10,"price":50,"water":"Low","risk":10,"season":["kharif","rabi","zaid"],"drought_ok":True},
    "Onion":      {"cost":20000,"yield_ton":10,"price":30,"water":"Medium","risk":35,"season":["rabi"],"drought_ok":False},
    "Garlic":     {"cost":25000,"yield_ton":5,"price":80,"water":"Medium","risk":30,"season":["rabi"],"drought_ok":False},
    "Soybean":    {"cost":12000,"yield_ton":2,"price":45,"water":"Medium","risk":25,"season":["kharif"],"drought_ok":False},
    "Banana":     {"cost":30000,"yield_ton":25,"price":35,"water":"High","risk":40,"season":["kharif","zaid"],"drought_ok":False},
    "Orange":     {"cost":20000,"yield_ton":8,"price":40,"water":"Medium","risk":30,"season":["rabi"],"drought_ok":False},
    "Jasmine":    {"cost":15000,"yield_ton":2,"price":200,"water":"Medium","risk":25,"season":["kharif","zaid"],"drought_ok":False},
    "Rice":       {"cost":20000,"yield_ton":5,"price":35,"water":"High","risk":30,"season":["kharif"],"drought_ok":False},
    "Sugarcane":  {"cost":35000,"yield_ton":40,"price":4,"water":"High","risk":25,"season":["zaid"],"drought_ok":False},
    "Maize":      {"cost":10000,"yield_ton":5,"price":20,"water":"Medium","risk":20,"season":["kharif","rabi"],"drought_ok":False},
    "Mustard":    {"cost":8000,"yield_ton":2,"price":55,"water":"Low","risk":20,"season":["rabi"],"drought_ok":True},
    "Litchi":     {"cost":25000,"yield_ton":6,"price":80,"water":"Medium","risk":35,"season":["rabi"],"drought_ok":False},
    "Wheat":      {"cost":12000,"yield_ton":4,"price":22,"water":"Medium","risk":15,"season":["rabi"],"drought_ok":False},
    "Carrot":     {"cost":10000,"yield_ton":8,"price":25,"water":"Medium","risk":20,"season":["rabi"],"drought_ok":False},
    "Watermelon": {"cost":12000,"yield_ton":15,"price":15,"water":"Medium","risk":25,"season":["zaid"],"drought_ok":False},
    "Cotton":     {"cost":22000,"yield_ton":2,"price":60,"water":"Medium","risk":45,"season":["kharif"],"drought_ok":False},
    "Jute":       {"cost":10000,"yield_ton":3,"price":42,"water":"High","risk":20,"season":["kharif"],"drought_ok":False},
    "Millet":     {"cost":6000,"yield_ton":2,"price":25,"water":"Low","risk":10,"season":["kharif"],"drought_ok":True},
    "Fern":       {"cost":8000,"yield_ton":1,"price":80,"water":"High","risk":20,"season":["kharif","rabi"],"drought_ok":False},
    "Plum":       {"cost":18000,"yield_ton":5,"price":70,"water":"Medium","risk":30,"season":["rabi"],"drought_ok":False},
    "Tuberose":   {"cost":12000,"yield_ton":2,"price":60,"water":"Medium","risk":20,"season":["kharif"],"drought_ok":False},
    "Jackfruit":  {"cost":15000,"yield_ton":10,"price":25,"water":"Medium","risk":15,"season":["zaid"],"drought_ok":True},
    "Paddy":      {"cost":20000,"yield_ton":5, "price":35, "water":"High",  "risk":25,"season":["kharif"],        "drought_ok":False},
    "Cotton":     {"cost":22000,"yield_ton":2, "price":60, "water":"Medium","risk":45,"season":["kharif"],        "drought_ok":False},
    "Redgram":    {"cost":12000,"yield_ton":1.5,"price":70,"water":"Low",   "risk":20,"season":["kharif"],        "drought_ok":True},
    "Chickpea":   {"cost":10000,"yield_ton":1.2,"price":60,"water":"Low",   "risk":15,"season":["rabi"],          "drought_ok":True},
    "Sunflower":  {"cost":10000,"yield_ton":1.5,"price":50,"water":"Low",   "risk":20,"season":["rabi","kharif"], "drought_ok":True},
    "Safflower":  {"cost":8000, "yield_ton":1,  "price":55,"water":"Low",   "risk":15,"season":["rabi"],          "drought_ok":True},
    "Moong":      {"cost":8000, "yield_ton":1,  "price":60,"water":"Low",   "risk":15,"season":["zaid","kharif"], "drought_ok":True},
    "Turmeric":   {"cost":25000,"yield_ton":6,  "price":80,"water":"Medium","risk":30,"season":["kharif"],        "drought_ok":False},
    "Tobacco":    {"cost":18000,"yield_ton":2,  "price":90,"water":"Medium","risk":40,"season":["rabi","kharif"], "drought_ok":False},
    "Cashew":     {"cost":15000,"yield_ton":1.5,"price":800,"water":"Low",  "risk":20,"season":["kharif"],        "drought_ok":True},
    "Ragi":       {"cost":8000, "yield_ton":2,  "price":30,"water":"Low",   "risk":10,"season":["kharif"],        "drought_ok":True},
    "Bajra":      {"cost":6000, "yield_ton":2,  "price":22,"water":"Low",   "risk":10,"season":["kharif"],        "drought_ok":True},
    "Jowar":      {"cost":7000, "yield_ton":2,  "price":22,"water":"Low",   "risk":10,"season":["kharif"],        "drought_ok":True},
    "Horsegram":  {"cost":6000, "yield_ton":1,  "price":55,"water":"Low",   "risk":10,"season":["rabi"],          "drought_ok":True},
    "Guar":       {"cost":6000, "yield_ton":1,  "price":40,"water":"Low",   "risk":10,"season":["kharif"],        "drought_ok":True},
    "Moth Bean":  {"cost":5000, "yield_ton":0.8,"price":45,"water":"Low",   "risk":10,"season":["kharif"],        "drought_ok":True},
    "Cumin":      {"cost":15000,"yield_ton":0.8,"price":150,"water":"Low",  "risk":25,"season":["rabi"],          "drought_ok":True},
    "Coriander":  {"cost":8000, "yield_ton":1,  "price":80,"water":"Low",   "risk":15,"season":["rabi"],          "drought_ok":True},
    "Pea":        {"cost":10000,"yield_ton":3,  "price":30,"water":"Medium","risk":20,"season":["rabi"],          "drought_ok":False},
    "Castor":     {"cost":8000, "yield_ton":1.5,"price":55,"water":"Low",   "risk":15,"season":["kharif"],        "drought_ok":True},
    "Arecanut":   {"cost":20000,"yield_ton":3,  "price":400,"water":"High", "risk":25,"season":["kharif"],        "drought_ok":False},
    "Coconut":    {"cost":15000,"yield_ton":8,  "price":25,"water":"Medium","risk":15,"season":["kharif","rabi","zaid"],"drought_ok":False},
    "Grapes":     {"cost":40000,"yield_ton":8,  "price":60,"water":"Medium","risk":40,"season":["rabi"],          "drought_ok":False},
    "Tur":        {"cost":12000,"yield_ton":1.5,"price":70,"water":"Low",   "risk":20,"season":["kharif"],        "drought_ok":True},
    "Sesame":     {"cost":7000, "yield_ton":0.8,"price":100,"water":"Low",  "risk":15,"season":["zaid","kharif"], "drought_ok":True},
    "Vegetables": {"cost":15000,"yield_ton":8,  "price":25,"water":"Medium","risk":25,"season":["kharif","rabi","zaid"],"drought_ok":False},
    "Flowers":    {"cost":12000,"yield_ton":3,  "price":50,"water":"Medium","risk":20,"season":["kharif","rabi"], "drought_ok":False},
    "Leafy Greens":     {"cost":8000,"yield_ton":5,"price":20,"water":"Medium","risk":15,"season":["kharif","rabi","zaid"],"drought_ok":False},
    "Leafy Vegetables": {"cost":8000,"yield_ton":5,"price":20,"water":"Medium","risk":15,"season":["rabi","zaid"], "drought_ok":False},
}

SOIL_HEALTH_ADVICE = {
    "Alluvial Soil": {
        "fertilizers": {
            "en": ["Urea 50kg/acre", "DAP 25kg/acre", "MOP 20kg/acre"],
            "hi": ["यूरिया 50kg/एकड़", "DAP 25kg/एकड़", "MOP 20kg/एकड़"],
            "te": ["యూరియా 50kg/ఎకరా", "DAP 25kg/ఎకరా", "MOP 20kg/ఎకరా"]
        },
        "organic": {
            "en": ["Vermicompost 2 ton/acre", "Green manure (Dhaincha)", "FYM 5 ton/acre"],
            "hi": ["वर्मीकम्पोस्ट 2 टन/एकड़", "हरी खाद (धैंचा)", "FYM 5 टन/एकड़"],
            "te": ["వర్మీకంపోస్ట్ 2 టన్/ఎకరా", "హరిత ఎరువు (ధైంచా)", "FYM 5 టన్/ఎకరా"]
        },
        "green_manure": {
            "en": "Grow Sunhemp or Dhaincha before main crop to fix nitrogen",
            "hi": "नाइट्रोजन स्थिरीकरण के लिए मुख्य फसल से पहले सनहेम्प या धैंचा उगाएं",
            "te": "నత్రజని స్థిరీకరణకు ప్రధాన పంట ముందు సన్‌హెంప్ లేదా ధైంచా పెంచండి"
        },
        "rotation": {
            "en": ["Sugarcane → Wheat → Mustard", "Maize → Potato → Onion"],
            "hi": ["गन्ना → गेहूं → सरसों", "मक्का → आलू → प्याज"],
            "te": ["చెరకు → గోధుమ → ఆవాలు", "మొక్కజొన్న → బంగాళాదుంప → ఉల్లి"]
        },
        "rotation_tip": {
            "en": "Rotate with legumes like Moong/Urad to restore nitrogen naturally",
            "hi": "नाइट्रोजन स्वाभाविक रूप से बहाल करने के लिए मूंग/उड़द दालों के साथ फसल चक्र करें",
            "te": "నత్రజనిని సహజంగా పునరుద్ధరించడానికి మూంగ్/ఉరద్ పప్పుధాన్యాలతో పంట మార్పిడి చేయండి"
        }
    },
    "Black Soil": {
        "fertilizers": {
            "en": ["Urea 40kg/acre", "SSP 30kg/acre (for phosphorus)", "Gypsum 100kg/acre"],
            "hi": ["यूरिया 40kg/एकड़", "SSP 30kg/एकड़ (फास्फोरस के लिए)", "जिप्सम 100kg/एकड़"],
            "te": ["యూరియా 40kg/ఎకరా", "SSP 30kg/ఎకరా (ఫాస్ఫరస్ కోసం)", "జిప్సమ్ 100kg/ఎకరా"]
        },
        "organic": {
            "en": ["FYM 4 ton/acre", "Neem cake 100kg/acre", "Vermicompost 1.5 ton/acre"],
            "hi": ["FYM 4 टन/एकड़", "नीम केक 100kg/एकड़", "वर्मीकम्पोस्ट 1.5 टन/एकड़"],
            "te": ["FYM 4 టన్/ఎకరా", "వేప పిండి 100kg/ఎకరా", "వర్మీకంపోస్ట్ 1.5 టన్/ఎకరా"]
        },
        "green_manure": {
            "en": "Grow Sesbania or Cowpea before cotton season to improve nitrogen",
            "hi": "नाइट्रोजन सुधारने के लिए कपास सीजन से पहले सेस्बानिया या लोबिया उगाएं",
            "te": "నత్రజని మెరుగుపరచడానికి పత్తి సీజన్ ముందు సెస్బానియా లేదా అలసంద పెంచండి"
        },
        "rotation": {
            "en": ["Cotton → Wheat → Chickpea", "Soybean → Jowar → Groundnut"],
            "hi": ["कपास → गेहूं → चना", "सोयाबीन → ज्वार → मूंगफली"],
            "te": ["పత్తి → గోధుమ → శనగ", "సోయాబీన్ → జొన్న → వేరుశెనగ"]
        },
        "rotation_tip": {
            "en": "Rotate Cotton with Pulses — pulses fix nitrogen and break pest cycles",
            "hi": "कपास को दालों के साथ फसल चक्र करें — दालें नाइट्रोजन स्थिर करती हैं",
            "te": "పత్తిని పప్పుధాన్యాలతో మార్పిడి చేయండి — పప్పులు నత్రజని నిలుపుతాయి"
        }
    },
    "Clay Soil": {
        "fertilizers": {
            "en": ["Urea 35kg/acre", "DAP 20kg/acre", "Add sand 2 ton/acre for drainage"],
            "hi": ["यूरिया 35kg/एकड़", "DAP 20kg/एकड़", "जल निकासी के लिए रेत 2 टन/एकड़"],
            "te": ["యూరియా 35kg/ఎకరా", "DAP 20kg/ఎకరా", "నీటి పారుదలకు ఇసుక 2 టన్/ఎకరా"]
        },
        "organic": {
            "en": ["Cocopeat to improve aeration", "FYM 3 ton/acre", "Rice husk ash for drainage"],
            "hi": ["वायु संचार सुधारने के लिए कोकोपीट", "FYM 3 टन/एकड़", "जल निकासी के लिए चावल की भूसी की राख"],
            "te": ["గాలి ప్రసరణకు కొకోపీట్", "FYM 3 టన్/ఎకరా", "నీటి పారుదలకు వరి పొట్టు బూడిద"]
        },
        "green_manure": {
            "en": "Add Sesbania or Pillipesara — helps break clay structure naturally",
            "hi": "सेस्बानिया या पिल्लीपेसर डालें — मिट्टी की संरचना को प्राकृतिक रूप से तोड़ता है",
            "te": "సెస్బానియా లేదా పిల్లిపెసర జోడించండి — మట్టి నిర్మాణాన్ని సహజంగా విచ్ఛిన్నం చేస్తుంది"
        },
        "rotation": {
            "en": ["Rice → Wheat → Mustard", "Broccoli → Onion → Potato"],
            "hi": ["चावल → गेहूं → सरसों", "ब्रोकली → प्याज → आलू"],
            "te": ["వరి → గోధుమ → ఆవాలు", "బ్రోకలీ → ఉల్లి → బంగాళాదుంప"]
        },
        "rotation_tip": {
            "en": "After paddy, grow a dry land crop like Wheat to break waterlogging cycle",
            "hi": "धान के बाद, जलजमाव चक्र तोड़ने के लिए गेहूं जैसी शुष्क भूमि फसल उगाएं",
            "te": "వరి తర్వాత, నీటి నిలకడ చక్రాన్ని విచ్ఛిన్నం చేయడానికి గోధుమ వంటి పంట పెంచండి"
        }
    },
    "Red Soil": {
        "fertilizers": {
            "en": ["Urea 60kg/acre", "DAP 35kg/acre (low phosphorus)", "MOP 25kg/acre", "Lime 200kg/acre to correct pH"],
            "hi": ["यूरिया 60kg/एकड़", "DAP 35kg/एकड़ (कम फास्फोरस)", "MOP 25kg/एकड़", "pH सुधारने के लिए चूना 200kg/एकड़"],
            "te": ["యూరియా 60kg/ఎకరా", "DAP 35kg/ఎకరా (తక్కువ ఫాస్ఫరస్)", "MOP 25kg/ఎకరా", "pH సరిచేయడానికి సున్నం 200kg/ఎకరా"]
        },
        "organic": {
            "en": ["Compost 4 ton/acre", "Neem cake 150kg/acre", "Bone meal for phosphorus"],
            "hi": ["कम्पोस्ट 4 टन/एकड़", "नीम केक 150kg/एकड़", "फास्फोरस के लिए हड्डी का चूरा"],
            "te": ["కంపోస్ట్ 4 టన్/ఎకరా", "వేప పిండి 150kg/ఎకరా", "ఫాస్ఫరస్ కోసం ఎముక పొడి"]
        },
        "green_manure": {
            "en": "Grow Groundnut as green manure — fixes nitrogen and adds organic matter",
            "hi": "हरी खाद के रूप में मूंगफली उगाएं — नाइट्रोजन स्थिर करती है और जैविक पदार्थ जोड़ती है",
            "te": "హరిత ఎరువుగా వేరుశెనగ పెంచండి — నత్రజని స్థిరీకరిస్తుంది మరియు సేంద్రీయ పదార్థం జోడిస్తుంది"
        },
        "rotation": {
            "en": ["Groundnut → Jowar → Chilli", "Tomato → Maize → Cowpea"],
            "hi": ["मूंगफली → ज्वार → मिर्च", "टमाटर → मक्का → लोबिया"],
            "te": ["వేరుశెనగ → జొన్న → మిర్చి", "టమాటా → మొక్కజొన్న → అలసంద"]
        },
        "rotation_tip": {
            "en": "Rotate Tomato/Chilli with Groundnut to reduce soil acidity and restore nutrients",
            "hi": "मिट्टी की अम्लता कम करने के लिए टमाटर/मिर्च को मूंगफली के साथ फसल चक्र करें",
            "te": "మట్టి ఆమ్లతను తగ్గించడానికి టమాటా/మిర్చిని వేరుశెనగతో మార్పిడి చేయండి"
        }
    }
}


WEATHER_DATA = {
    "Andhra Pradesh": {"temp":28,"rainfall":"moderate","humidity":70,"drought_prob":20},
    "Telangana":      {"temp":30,"rainfall":"moderate","humidity":65,"drought_prob":25},
    "Maharashtra":    {"temp":27,"rainfall":"moderate","humidity":60,"drought_prob":30},
    "Karnataka":      {"temp":26,"rainfall":"good","humidity":72,"drought_prob":15},
    "Tamil Nadu":     {"temp":29,"rainfall":"good","humidity":75,"drought_prob":10},
    "Uttar Pradesh":  {"temp":24,"rainfall":"moderate","humidity":60,"drought_prob":25},
    "Punjab":         {"temp":22,"rainfall":"low","humidity":55,"drought_prob":30},
    "Rajasthan":      {"temp":33,"rainfall":"low","humidity":35,"drought_prob":60},
    "Madhya Pradesh": {"temp":26,"rainfall":"moderate","humidity":62,"drought_prob":28},
    "Gujarat":        {"temp":30,"rainfall":"low","humidity":50,"drought_prob":40},
}

SUCCESS_STORIES = {
    "Telangana": {
        "Warangal":    {"crop":"Cotton","percent":72,"season":"Kharif","profit":"₹85,000/acre"},
        "Nizamabad":   {"crop":"Turmeric","percent":68,"season":"Kharif","profit":"₹1,20,000/acre"},
        "Khammam":     {"crop":"Maize","percent":75,"season":"Kharif","profit":"₹45,000/acre"},
        "Nalgonda":    {"crop":"Chilli","percent":65,"season":"Rabi","profit":"₹95,000/acre"},
        "Karimnagar":  {"crop":"Paddy","percent":80,"season":"Kharif","profit":"₹40,000/acre"},
        "Adilabad":    {"crop":"Soybean","percent":60,"season":"Kharif","profit":"₹55,000/acre"},
        "Mancherial":  {"crop":"Cotton","percent":78,"season":"Kharif","profit":"₹80,000/acre"},
    },
    "Andhra Pradesh": {
        "Guntur":      {"crop":"Chilli","percent":82,"season":"Rabi","profit":"₹1,10,000/acre"},
        "Kurnool":     {"crop":"Groundnut","percent":70,"season":"Kharif","profit":"₹65,000/acre"},
        "Anantapur":   {"crop":"Groundnut","percent":75,"season":"Kharif","profit":"₹60,000/acre"},
        "Vijayawada":  {"crop":"Sugarcane","percent":65,"season":"Zaid","profit":"₹90,000/acre"},
    },
    "Maharashtra": {
        "Nashik":      {"crop":"Onion","percent":78,"season":"Rabi","profit":"₹75,000/acre"},
        "Pune":        {"crop":"Tomato","percent":70,"season":"Kharif","profit":"₹80,000/acre"},
        "Nagpur":      {"crop":"Orange","percent":65,"season":"Rabi","profit":"₹95,000/acre"},
    },
}

FARMING_CALENDAR = {
    "Tomato": {
        "kharif": {"sow":"June 1-15","transplant":"July 1-15","fertilize1":"July 20","fertilize2":"Aug 20","irrigate":"Every 5-7 days","harvest":"Sep 15 - Oct 30","duration":"120 days"},
        "rabi":   {"sow":"Oct 15-30","transplant":"Nov 15","fertilize1":"Dec 1","fertilize2":"Jan 1","irrigate":"Every 7-10 days","harvest":"Feb 15 - Mar 30","duration":"130 days"},
    },
    "Rice": {
        "kharif": {"sow":"June 15-30","transplant":"July 15","fertilize1":"Aug 1","fertilize2":"Sep 1","irrigate":"Keep flooded 5cm","harvest":"Oct 15 - Nov 15","duration":"120 days"},
    },
    "Wheat": {
        "rabi": {"sow":"Nov 1-20","transplant":"Direct sowing","fertilize1":"Nov 25","fertilize2":"Jan 15","irrigate":"Every 20-25 days","harvest":"Mar 15 - Apr 15","duration":"120 days"},
    },
    "Chilli": {
        "kharif": {"sow":"May 15-30","transplant":"July 1","fertilize1":"July 20","fertilize2":"Sep 1","irrigate":"Every 7 days","harvest":"Oct - Dec","duration":"150 days"},
        "rabi":   {"sow":"Sep 15-30","transplant":"Oct 20","fertilize1":"Nov 10","fertilize2":"Dec 15","irrigate":"Every 10 days","harvest":"Feb - Apr","duration":"150 days"},
    },
    "Cotton": {
        "kharif": {"sow":"May 1-15","transplant":"Direct sowing","fertilize1":"June 15","fertilize2":"Aug 1","irrigate":"Every 10-15 days","harvest":"Oct - Jan","duration":"180 days"},
    },
    "Maize": {
        "kharif": {"sow":"June 15-30","transplant":"Direct sowing","fertilize1":"July 15","fertilize2":"Aug 15","irrigate":"Every 8-10 days","harvest":"Sep 15 - Oct 15","duration":"90 days"},
        "rabi":   {"sow":"Oct 15-30","transplant":"Direct sowing","fertilize1":"Nov 15","fertilize2":"Dec 15","irrigate":"Every 10 days","harvest":"Feb - Mar","duration":"100 days"},
    },
    "Groundnut": {
        "kharif": {"sow":"June 15-July 1","transplant":"Direct sowing","fertilize1":"July 20","fertilize2":"Aug 20","irrigate":"Every 10-12 days","harvest":"Oct 1-30","duration":"105 days"},
        "zaid":   {"sow":"Jan 15-Feb 1","transplant":"Direct sowing","fertilize1":"Feb 20","fertilize2":"Mar 20","irrigate":"Every 8 days","harvest":"May 1-30","duration":"105 days"},
    },
    "Onion": {
        "rabi": {"sow":"Oct 1-15 (nursery)","transplant":"Nov 15-30","fertilize1":"Dec 15","fertilize2":"Jan 20","irrigate":"Every 7-10 days","harvest":"Mar - Apr","duration":"150 days"},
    },
    "Mustard": {
        "rabi": {"sow":"Oct 1-20","transplant":"Direct sowing","fertilize1":"Oct 25","fertilize2":"Dec 1","irrigate":"Every 20-25 days","harvest":"Feb 1-28","duration":"120 days"},
    },
    "Sugarcane": {
        "zaid": {"sow":"Feb 1-Mar 15","transplant":"Direct sowing","fertilize1":"Mar 20","fertilize2":"June 1","irrigate":"Every 10 days","harvest":"Dec - Feb (next year)","duration":"365 days"},
    },
}
def get_live_crop_price(crop_name, state, district):
    """Fetch live mandi price from data.gov.in Agmarknet API"""
    import requests

    CROP_MAP = {
        'Tomato':'Tomato', 'Onion':'Onion', 'Potato':'Potato',
        'Chilli':'Chilli(Dry)', 'Maize':'Maize', 'Paddy':'Paddy(Common)',
        'Cotton':'Cotton', 'Soybean':'Soyabean', 'Groundnut':'Groundnut',
        'Wheat':'Wheat', 'Rice':'Rice', 'Turmeric':'Turmeric',
        'Redgram':'Arhar (Tur/Red Gram)(Whole)',
        'Chickpea':'Bengal Gram(Gram)(Whole)',
        'Sunflower':'Sunflower', 'Mustard':'Mustard',
        'Moong':'Moong (Whole)', 'Garlic':'Garlic',
        'Banana':'Banana', 'Mango':'Mango',
        'Jowar':'Jowar(Sorghum)', 'Bajra':'Bajra(Pearl Millet/Cumbu)',
        'Ragi':'Ragi (Finger Millet)', 'Castor':'Castor Seed',
        'Sesame':'Sesamum(Sesame/Til)', 'Cumin':'Cummin Seed(Jeera)',
        'Coriander':'Coriander(Leaves)', 'Ginger':'Ginger(Dry)',
        'Horsegram':'Horse Gram', 'Coconut':'Coconut',
        'Grapes':'Grapes', 'Watermelon':'Water Melon',
        'Brinjal':'Brinjal', 'Sugarcane':'Sugarcane',
        'Tobacco':'Tobacco', 'Tur':'Arhar (Tur/Red Gram)(Whole)',
    }

    agmark_name = CROP_MAP.get(crop_name)
    if not agmark_name:
        # No API mapping — use fallback price directly
        if crop_name in MANDI_PRICES:
            return MANDI_PRICES[crop_name]
        return None, None

    # ── Try live API ─────────────────────────────────────────────
    try:
        url = (
            "https://api.data.gov.in/resource/"
            "9ef84268-d588-465a-a308-a864a43d0070"
            f"?api-key={DATAGOV_KEY}"
            "&format=json&limit=5"
            f"&filters[State.Keyword]={state}"
            f"&filters[Commodity]={agmark_name}"
        )
        resp    = requests.get(url, timeout=3
                               
                               )
        data    = resp.json()
        records = data.get('records', [])

        if records:
            modal = float(records[0].get('Modal_Price', 0))
            if modal > 0:
                price_per_kg = round(modal / 100, 2)
                demand = 'high' if modal > 2000 else 'medium'
                print(f"✅ LIVE price {crop_name} in {state}: ₹{price_per_kg}/kg")
                return price_per_kg, demand

    except Exception as e:
        print(f"⚠️ Agmarknet error for {crop_name}: {e}")

    # ── Fallback to average prices ────────────────────────────────
    if crop_name in MANDI_PRICES:
        price, demand = MANDI_PRICES[crop_name]
        print(f"📊 Fallback price {crop_name}: ₹{price}/kg")
        return price, demand

    return None, None

def get_weather(state, district=None):
    
    # Exact lat/lon coordinates for every Telangana district
    DISTRICT_COORDS = {
        # TELANGANA — all 33 districts
        "Hyderabad":                  (17.3850, 78.4867),
        "Adilabad":                   (19.6640, 78.5320),
        "Bhadradri Kothagudem":       (17.5560, 80.6190),
        "Hanamkonda":                 (17.9784, 79.5941),
        "Jagtial":                    (18.7940, 78.9140),
        "Jangaon":                    (17.7240, 79.1520),
        "Jayashankar Bhupalpally":    (18.4420, 79.8910),
        "Jogulamba Gadwal":           (16.2340, 77.8030),
        "Kamareddy":                  (18.3220, 78.3400),
        "Karimnagar":                 (18.4386, 79.1288),
        "Khammam":                    (17.2473, 80.1514),
        "Komaram Bheem Asifabad":     (19.3660, 79.2800),
        "Mahabubabad":                (17.5990, 80.0020),
        "Mahabubnagar":               (16.7374, 77.9870),
        "Mancherial":                 (18.8700, 79.4600),
        "Medak":                      (18.0440, 78.2630),
        "Medchal-Malkajgiri":         (17.5540, 78.5320),
        "Mulugu":                     (18.1960, 80.0540),
        "Nagarkurnool":               (16.4800, 78.3240),
        "Nalgonda":                   (17.0500, 79.2660),
        "Narayanpet":                 (16.7440, 77.4940),
        "Nirmal":                     (19.0940, 78.3440),
        "Nizamabad":                  (18.6725, 78.0941),
        "Peddapalli":                 (18.6150, 79.3830),
        "Rajanna Sircilla":           (18.3870, 78.8120),
        "Rangareddy":                 (17.3616, 78.3837),
        "Sangareddy":                 (17.6240, 78.0870),
        "Siddipet":                   (18.1020, 78.8520),
        "Suryapet":                   (17.1410, 79.6220),
        "Vikarabad":                  (17.3370, 77.9050),
        "Wanaparthy":                 (16.3620, 78.0640),
        "Warangal":                   (17.9784, 79.5941),
        "Yadadri Bhuvanagiri":        (17.5600, 78.9920),

        # ANDHRA PRADESH
        "Visakhapatnam":              (17.6868, 83.2185),
        "Vijayawada":                 (16.5062, 80.6480),
        "Guntur":                     (16.3067, 80.4365),
        "Kurnool":                    (15.8281, 78.0373),
        "Nellore":                    (14.4426, 79.9865),
        "Tirupati":                   (13.6288, 79.4192),
        "Anantapur":                  (14.6819, 77.6006),
        "Kadapa":                     (14.4674, 78.8241),
        "Eluru":                      (16.7107, 81.0952),
        "Ongole":                     (15.5057, 80.0499),

        # MAHARASHTRA
        "Mumbai":                     (19.0760, 72.8777),
        "Pune":                       (18.5204, 73.8567),
        "Nagpur":                     (21.1458, 79.0882),
        "Nashik":                     (19.9975, 73.7898),
        "Aurangabad":                 (19.8762, 75.3433),
        "Solapur":                    (17.6805, 75.9064),
        "Kolhapur":                   (16.7050, 74.2433),
        "Amravati":                   (20.9374, 77.7796),
        "Sangli":                     (16.8524, 74.5815),
        "Latur":                      (18.4088, 76.5604),

        # KARNATAKA
        "Bengaluru":                  (12.9716, 77.5946),
        "Mysuru":                     (12.2958, 76.6394),
        "Hubli":                      (15.3647, 75.1240),
        "Mangaluru":                  (12.9141, 74.8560),
        "Belagavi":                   (15.8497, 74.4977),
        "Dharwad":                    (15.4589, 75.0078),
        "Vijayapura":                 (16.8302, 75.7100),
        "Davanagere":                 (14.4644, 75.9218),
        "Shimoga":                    (13.9299, 75.5681),
        "Tumkur":                     (13.3409, 77.1010),

        # TAMIL NADU
        "Chennai":                    (13.0827, 80.2707),
        "Coimbatore":                 (11.0168, 76.9558),
        "Madurai":                    (9.9252, 78.1198),
        "Salem":                      (11.6643, 78.1460),
        "Trichy":                     (10.7905, 78.7047),
        "Tirunelveli":                (8.7139, 77.7567),
        "Vellore":                    (12.9165, 79.1325),
        "Erode":                      (11.3410, 77.7172),
        "Dindigul":                   (10.3624, 77.9695),
        "Thanjavur":                  (10.7867, 79.1378),

        # UTTAR PRADESH
        "Lucknow":                    (26.8467, 80.9462),
        "Kanpur":                     (26.4499, 80.3319),
        "Agra":                       (27.1767, 78.0081),
        "Varanasi":                   (25.3176, 82.9739),
        "Allahabad":                  (25.4358, 81.8463),
        "Meerut":                     (28.9845, 77.7064),
        "Ghaziabad":                  (28.6692, 77.4538),
        "Gorakhpur":                  (26.7606, 83.3732),
        "Aligarh":                    (27.8974, 78.0880),
        "Moradabad":                  (28.8386, 78.7733),

        # PUNJAB
        "Ludhiana":                   (30.9010, 75.8573),
        "Amritsar":                   (31.6340, 74.8723),
        "Jalandhar":                  (31.3260, 75.5762),
        "Patiala":                    (30.3398, 76.3869),
        "Bathinda":                   (30.2110, 74.9455),
        "Mohali":                     (30.7046, 76.7179),
        "Pathankot":                  (32.2643, 75.6421),
        "Hoshiarpur":                 (31.5143, 75.9113),
        "Gurdaspur":                  (32.0396, 75.4058),
        "Firozpur":                   (30.9254, 74.6130),

        # RAJASTHAN
        "Jaipur":                     (26.9124, 75.7873),
        "Jodhpur":                    (26.2389, 73.0243),
        "Udaipur":                    (24.5854, 73.7125),
        "Kota":                       (25.2138, 75.8648),
        "Bikaner":                    (28.0229, 73.3119),
        "Ajmer":                      (26.4499, 74.6399),
        "Bhilwara":                   (25.3463, 74.6313),
        "Alwar":                      (27.5530, 76.6346),
        "Bharatpur":                  (27.2152, 77.5030),
        "Sikar":                      (27.6094, 75.1399),

        # MADHYA PRADESH
        "Bhopal":                     (23.2599, 77.4126),
        "Indore":                     (22.7196, 75.8577),
        "Gwalior":                    (26.2183, 78.1828),
        "Jabalpur":                   (23.1815, 79.9864),
        "Ujjain":                     (23.1765, 75.7885),
        "Sagar":                      (23.8388, 78.7378),
        "Rewa":                       (24.5362, 81.2961),
        "Satna":                      (24.5694, 80.8322),
        "Dewas":                      (22.9676, 76.0534),
        "Chhindwara":                 (22.0574, 78.9382),

        # GUJARAT
        "Ahmedabad":                  (23.0225, 72.5714),
        "Surat":                      (21.1702, 72.8311),
        "Vadodara":                   (22.3072, 73.1812),
        "Rajkot":                     (22.3039, 70.8022),
        "Bhavnagar":                  (21.7645, 72.1519),
        "Jamnagar":                   (22.4707, 70.0577),
        "Gandhinagar":                (23.2156, 72.6369),
        "Anand":                      (22.5645, 72.9289),
        "Mehsana":                    (23.6002, 72.3693),
        "Junagadh":                   (21.5222, 70.4579),
    }

    # State capital fallback coordinates
    STATE_COORDS = {
        "Telangana":       (17.3850, 78.4867),
        "Andhra Pradesh":  (16.5062, 80.6480),
        "Maharashtra":     (19.0760, 72.8777),
        "Karnataka":       (12.9716, 77.5946),
        "Tamil Nadu":      (13.0827, 80.2707),
        "Uttar Pradesh":   (26.8467, 80.9462),
        "Punjab":          (30.9010, 75.8573),
        "Rajasthan":       (26.9124, 75.7873),
        "Madhya Pradesh":  (23.2599, 77.4126),
        "Gujarat":         (23.0225, 72.5714),
    }

    # Get coordinates
    coords = DISTRICT_COORDS.get(district) or STATE_COORDS.get(state, (17.3850, 78.4867))
    lat, lon = coords

    try:
        import requests
        url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OPENWEATHER_KEY}&units=metric"
        response = requests.get(url, timeout=5)
        data = response.json()

        if response.status_code == 200:
            temp        = round(data['main']['temp'])
            humidity    = data['main']['humidity']
            rainfall    = data.get('rain', {}).get('1h', 0)
            weather_main = data['weather'][0]['main'].lower()
            description = data['weather'][0]['description'].title()
            city_name   = data.get('name', district or state)

            # Calculate rainfall category and drought probability
            if rainfall > 5 or weather_main in ['rain','thunderstorm','drizzle']:
                rainfall_label = "heavy"
                drought_prob   = 5
            elif rainfall > 1 or weather_main == 'clouds' and humidity > 75:
                rainfall_label = "good"
                drought_prob   = 15
            elif humidity > 60:
                rainfall_label = "moderate"
                drought_prob   = 25
            elif humidity > 40:
                rainfall_label = "low"
                drought_prob   = 45
            else:
                rainfall_label = "very low"
                drought_prob   = 70

            print(f"✅ LIVE weather for {district or state} ({lat},{lon}): {temp}°C, {humidity}%, {description}")
            return {
                "temp"        : temp,
                "rainfall"    : rainfall_label,
                "humidity"    : humidity,
                "drought_prob": drought_prob,
                "city"        : city_name,
                "description" : description,
                "real"        : True
            }

    except Exception as e:
        print(f"⚠️ Weather API error for {district}: {e} — using fallback")

    # Fallback
    return WEATHER_DATA.get(state, {
        "temp": 27, "rainfall": "moderate",
        "humidity": 65, "drought_prob": 25,
        "real": False
    })
    
def get_risk_score(crop_name, soil_type, season, weather):
    base = CROP_DETAILS.get(crop_name, {}).get("risk", 40)
    # Weather adjustment
    if weather["drought_prob"] > 40 and not CROP_DETAILS.get(crop_name,{}).get("drought_ok", False):
        base += 20
    if weather["drought_prob"] > 40 and CROP_DETAILS.get(crop_name,{}).get("drought_ok", True):
        base -= 10
    # Soil health score adjustment
    soil_score = SOIL_DATA.get(soil_type, {}).get("health_score", 7)
    if soil_score >= 9:   base -= 10
    elif soil_score >= 7: base -= 5
    elif soil_score < 6:  base += 10
    return max(5, min(95, base))

def get_profit_estimate(crop_name, acres=1):
    d = CROP_DETAILS.get(crop_name, {})
    if not d: return None
    cost     = d.get("cost", 15000) * acres
    revenue  = d.get("yield_ton", 3) * 1000 * d.get("price", 20) * acres
    profit   = revenue - cost
    return {"cost": cost, "revenue": revenue, "profit": profit,
            "yield_ton": d.get("yield_ton",3)*acres,
            "price_per_kg": d.get("price",20),
            "water": d.get("water","Medium"),
            "risk": d.get("risk",40)}

def get_alternative_crops(soil_type, season, weather):
    alts = []
    soil_crops = SOIL_DATA.get(soil_type, {}).get("crops", {})
    all_crops = []
    for cat, items in soil_crops.items():
        for item in items:
            all_crops.append(item["name"])
    drought_mode = weather.get("drought_prob", 0) > 40
    for c in all_crops:
        d = CROP_DETAILS.get(c, {})
        ok_season  = season.lower() in [s.lower() for s in d.get("season", [])]
        ok_drought = (not drought_mode) or d.get("drought_ok", False)
        if ok_season and ok_drought:
            alts.append(c)
    return alts[:5]

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ═══════════════════════════════════════════════════════════════
# CNN MODEL — Soil Classification (Your trained model)
# Classes must match soil_class_info.json exactly!
# ═══════════════════════════════════════════════════════════════
SOIL_MODEL = None
# ⚠️ These 4 classes match YOUR dataset (Alluvial, Black, Clay, Red)
# Order from soil_class_info.json — alphabetical
SOIL_CLASSES = ['Alluvial Soil', 'Black Soil', 'Clay Soil', 'Red Soil']

def load_soil_model():
    global SOIL_MODEL
    if SOIL_MODEL is not None:
        return SOIL_MODEL

    import os as _os
    base_dir   = _os.path.dirname(_os.path.abspath(__file__))
    models_dir = _os.path.join(base_dir, 'models')

    # Paths to try — in order of preference
    keras_path      = _os.path.join(models_dir, 'soil_model_fixed.keras')
    savedmodel_path = _os.path.join(models_dir, 'soil_model_savedmodel')
    h5_path         = _os.path.join(models_dir, 'soil_model.h5')

    try:
        import tensorflow as tf

        # ── Strategy 1: .keras format (most compatible with TF 2.20) ──
        if _os.path.exists(keras_path):
            try:
                SOIL_MODEL = tf.keras.models.load_model(keras_path, compile=False)
                print(f'✅ Soil model loaded (.keras format)! Classes: {SOIL_CLASSES}')
                return SOIL_MODEL
            except Exception as e1:
                print(f'   .keras load failed: {e1}')

        # ── Strategy 2: SavedModel folder format ──────────────────────
        if _os.path.exists(savedmodel_path):
            try:
                SOIL_MODEL = tf.keras.models.load_model(savedmodel_path, compile=False)
                print(f'✅ Soil model loaded (SavedModel)! Classes: {SOIL_CLASSES}')
                return SOIL_MODEL
            except Exception as e2:
                print(f'   SavedModel load failed: {e2}')

        # ── Strategy 3: Original .h5 with compile=False ───────────────
        if _os.path.exists(h5_path):
            try:
                SOIL_MODEL = tf.keras.models.load_model(h5_path, compile=False)
                print(f'✅ Soil model loaded (.h5 compile=False)! Classes: {SOIL_CLASSES}')
                return SOIL_MODEL
            except Exception as e3:
                print(f'   .h5 load failed: {e3}')
                print(f'   → Run CONVERT_MODEL_COLAB.ipynb to fix the model format')
        else:
            print(f'⚠️  No model file found in: {models_dir}')
            print(f'   Expected one of:')
            print(f'   → soil_model_fixed.keras')
            print(f'   → soil_model_savedmodel/ (folder)')
            print(f'   → soil_model.h5')

        print('⚠️  Model load failed — using HSV color analysis fallback')

    except ImportError:
        print('⚠️  TensorFlow not installed. Run: pip install tensorflow')
    except Exception as e:
        print(f'⚠️  Unexpected error loading model: {e}')

    return SOIL_MODEL

def classify_soil(image_path):
    """Real CNN prediction using your trained soil_model.h5"""
    import numpy as np

    # ── Layer 1: Real CNN Model ─────────────────────────────────
    model = load_soil_model()
    if model is not None:
        try:
            import tensorflow as tf
            img = tf.keras.preprocessing.image.load_img(image_path, target_size=(224, 224))
            img_array = tf.keras.preprocessing.image.img_to_array(img) / 255.0
            img_array = np.expand_dims(img_array, axis=0)
            prediction = model.predict(img_array, verbose=0)[0]
            predicted_class = SOIL_CLASSES[np.argmax(prediction)]
            confidence = float(np.max(prediction)) * 100
            print(f'🌱 CNN Soil → {predicted_class} ({confidence:.1f}% confidence)')
            return predicted_class
        except Exception as e:
            print(f'CNN prediction error: {e}')

    # ── Layer 2: HSV Color Analysis fallback ────────────────────
    try:
        from PIL import Image
        img = Image.open(image_path).convert('RGB')
        w, h = img.size
        cropped = img.crop((int(w*0.1), int(h*0.1), int(w*0.9), int(h*0.9)))
        small = cropped.resize((150, 150))
        arr = np.array(small, dtype=np.float32)
        r = arr[:,:,0].mean()
        g = arr[:,:,1].mean()
        b = arr[:,:,2].mean()
        bright = (r + g + b) / 3
        hsv = np.array(small.convert('HSV'), dtype=np.float32)
        sat = hsv[:,:,1].mean() / 255.0
        print(f'HSV fallback: r={r:.0f} g={g:.0f} b={b:.0f} sat={sat:.2f} bright={bright:.0f}')
        if sat < 0.18:
            return 'Black Soil'
        elif r - g > 20 and r - b > 25 and r > 130:
            return 'Red Soil'
        elif bright > 180 and sat < 0.28:
            return 'Alluvial Soil'
        else:
            return 'Clay Soil'
    except Exception as e:
        print(f'HSV fallback error: {e}')

    # ── Layer 3: Last resort ─────────────────────────────────────
    return random.choices(SOIL_CLASSES, weights=[0.25, 0.25, 0.25, 0.25])[0]

# ═══════════════════════════════════════════════════════════════
# CNN MODEL — Disease Detection (Random until disease model trained)
# ═══════════════════════════════════════════════════════════════
DISEASE_MODEL = None
DISEASE_CLASSES = [
    'Bacterial Wilt', 'Healthy Plant', 'Leaf Rust',
    'Powdery Mildew', 'Rice Blast', 'Tomato Late Blight', 'Yellow Mosaic Virus'
]

def load_disease_model():
    global DISEASE_MODEL
    if DISEASE_MODEL is not None:
        return DISEASE_MODEL
    try:
        import tensorflow as tf
        model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models', 'disease_model.h5')
        if os.path.exists(model_path):
            DISEASE_MODEL = tf.keras.models.load_model(model_path)
            print(f'✅ Disease model loaded!')
        else:
            print('⚠️  disease_model.h5 not found — using weighted random fallback')
    except Exception as e:
        print(f'⚠️  Disease model load error: {e}')
    return DISEASE_MODEL

def detect_plant_disease(image_path):
    """Real CNN prediction if disease_model.h5 exists, else weighted random."""
    import numpy as np

    # ── Real CNN model (if trained & available) ──────────────────
    model = load_disease_model()
    if model is not None:
        try:
            import tensorflow as tf
            img = tf.keras.preprocessing.image.load_img(image_path, target_size=(224, 224))
            img_array = tf.keras.preprocessing.image.img_to_array(img) / 255.0
            img_array = np.expand_dims(img_array, axis=0)
            prediction = model.predict(img_array, verbose=0)[0]
            predicted_class = DISEASE_CLASSES[np.argmax(prediction)]
            confidence = float(np.max(prediction)) * 100
            print(f'🔬 CNN Disease → {predicted_class} ({confidence:.1f}%)')
            if predicted_class in DISEASES:
                return predicted_class
        except Exception as e:
            print(f'Disease CNN error: {e}')

    # ── Weighted random fallback ──────────────────────────────────
    diseases = list(DISEASES.keys())
    weights = [0.25, 0.18, 0.15, 0.15, 0.12, 0.10, 0.05]
    return random.choices(diseases, weights=weights[:len(diseases)])[0]

def get_mandi_prices_for_district(crop_name, state, district):
    import requests
    CROP_MAP = {
        'Tomato':'Tomato','Onion':'Onion','Potato':'Potato',
        'Chilli':'Chilli(Dry)','Maize':'Maize',
        'Paddy':'Paddy(Common)','Cotton':'Cotton',
        'Soybean':'Soyabean','Groundnut':'Groundnut',
        'Wheat':'Wheat','Rice':'Rice','Turmeric':'Turmeric',
        'Redgram':'Arhar (Tur/Red Gram)(Whole)',
        'Chickpea':'Bengal Gram(Gram)(Whole)',
        'Sunflower':'Sunflower','Mustard':'Mustard',
        'Moong':'Moong (Whole)','Garlic':'Garlic',
        'Banana':'Banana','Mango':'Mango',
        'Jowar':'Jowar(Sorghum)',
        'Bajra':'Bajra(Pearl Millet/Cumbu)',
        'Ragi':'Ragi (Finger Millet)',
        'Castor':'Castor Seed',
        'Sesame':'Sesamum(Sesame/Til)',
        'Cumin':'Cummin Seed(Jeera)',
        'Coriander':'Coriander(Leaves)',
        'Ginger':'Ginger(Dry)','Horsegram':'Horse Gram',
        'Coconut':'Coconut','Grapes':'Grapes',
        'Watermelon':'Water Melon','Brinjal':'Brinjal',
        'Sugarcane':'Sugarcane','Tobacco':'Tobacco',
        'Tur':'Arhar (Tur/Red Gram)(Whole)',
    }
    agmark_name = CROP_MAP.get(crop_name)
    if not agmark_name:
        return []
    try:
        # Try state-specific first, fall back to all India
        url = (
            "https://api.data.gov.in/resource/"
            "9ef84268-d588-465a-a308-a864a43d0070"
            f"?api-key={DATAGOV_KEY}"
            "&format=json&limit=20"
            f"&filters[commodity]={agmark_name}"
        )
        print(f"🔍 Mandi URL: {url}")
        resp    = requests.get(url, timeout=4
                               )
        data    = resp.json()
        records = data.get('records', [])
        if not records:
            return []
        mandis = []
        for r in records:
            try:
                modal = float(r.get('modal_price', 0))
                min_p = float(r.get('min_price',   0))
                max_p = float(r.get('max_price',   0))
                if modal <= 0:
                    continue
                mandis.append({
                    'mandi'   : r.get('market',   'Unknown'),
                    'district': r.get('district', district),
                    'state'   : r.get('state',    state),
                    'min'     : round(min_p / 100, 2),
                    'modal'   : round(modal / 100, 2),
                    'max'     : round(max_p  / 100, 2),
                    'date'    : r.get('arrival_date', 'Today'),
                })
            except Exception as ex:
                continue

        mandis.sort(key=lambda x: x['modal'], reverse=True)
        return mandis[:10]
      
       
       
    except Exception as e:
        print(f"⚠️ Mandi list error for {crop_name}: {e}")
        return []

def get_market_prices(crop_name, state):
    price = MarketPrice.query.filter_by(crop_name=crop_name).first()
    if price:
        return price.price_per_kg, price.demand
    return None, None

def generate_reset_token():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=32))

def send_reply_email(farmer_name, farmer_email, subject, original_message, reply_text):
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f'🌾 BHUMI Team replied to your query — {subject}'
        msg['From'] = f'BHUMI Smart Agriculture <{MAIL_USERNAME}>'
        msg['To'] = farmer_email
        html = f"""
        <html><body style="font-family:Arial,sans-serif;background:#f5f9f5;padding:20px;">
        <div style="max-width:600px;margin:0 auto;background:white;border-radius:16px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,0.1);">
          <div style="background:linear-gradient(135deg,#2d6a4f,#40916c);padding:30px;text-align:center;">
            <h1 style="color:white;margin:0;font-size:1.8rem;">🌾 BHUMI</h1>
            <p style="color:rgba(255,255,255,0.9);margin:5px 0 0;">Smart Agriculture System</p>
          </div>
          <div style="padding:30px;">
            <p style="color:#333;font-size:1rem;">Dear <strong>{farmer_name}</strong>,</p>
            <p style="color:#555;">Our agriculture team has replied to your query:</p>
            <div style="background:#f5f5f5;border-radius:10px;padding:15px;margin:15px 0;border-left:4px solid #aaa;">
              <strong style="color:#666;font-size:.85rem;">YOUR QUERY ({subject}):</strong>
              <p style="color:#555;margin:8px 0 0;">{original_message}</p>
            </div>
            <div style="background:#e8f5e9;border-radius:10px;padding:15px;margin:15px 0;border-left:4px solid #40916c;">
              <strong style="color:#2d6a4f;font-size:.85rem;">🌾 BHUMI TEAM REPLY:</strong>
              <p style="color:#2d6a4f;margin:8px 0 0;font-size:1rem;">{reply_text}</p>
            </div>
            <p style="color:#555;font-size:.9rem;">Login to BHUMI app to see full details.</p>
            <div style="text-align:center;margin-top:25px;">
              <a href="http://localhost:5000/help" style="background:linear-gradient(135deg,#2d6a4f,#40916c);color:white;padding:12px 30px;border-radius:25px;text-decoration:none;font-weight:bold;">Open BHUMI App</a>
            </div>
          </div>
          <div style="background:#f5f9f5;padding:15px;text-align:center;border-top:1px solid #eee;">
            <p style="color:#888;font-size:.8rem;margin:0;">🌾 BHUMI Smart Agriculture | Built for Indian Farmers</p>
            <p style="color:#888;font-size:.8rem;margin:4px 0 0;">Kisan Helpline: 1800-180-1551 (Free)</p>
          </div>
        </div>
        </body></html>
        """
        msg.attach(MIMEText(html, 'html'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(MAIL_USERNAME, MAIL_PASSWORD)
        server.sendmail(MAIL_USERNAME, farmer_email, msg.as_string())
        server.quit()
        print(f'✅ Reply email sent to {farmer_email}')
        return True
    except Exception as e:
        print(f'❌ Email error: {e}')
        return False
    
def get_unread_count():
    if current_user.is_authenticated and current_user.is_admin:
        return ContactMessage.query.filter_by(is_read=False).count()
    return 0

app.jinja_env.globals['get_unread_count'] = get_unread_count

# ─────────────────────────────────────────────
# ROUTES - AUTH
# ─────────────────────────────────────────────
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        farmer = Farmer.query.filter_by(email=email).first()
        if farmer and check_password_hash(farmer.password, password):
            login_user(farmer)
            session['language'] = farmer.language or 'en'
            if not farmer.language or farmer.language == 'en':
                return redirect(url_for('select_language'))
            return redirect(url_for('home'))
        flash('Invalid email or password. Please try again.', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        state = request.form.get('state', '')
        district = request.form.get('district', '')
        if not all([name, phone, email, password, state, district]):
            flash('All fields are required!', 'danger')
            return render_template('register.html', states=list(STATES_DISTRICTS.keys()), districts=STATES_DISTRICTS)
        if Farmer.query.filter_by(email=email).first():
            flash('Email already registered! Please login.', 'danger')
            return render_template('register.html', states=list(STATES_DISTRICTS.keys()), districts=STATES_DISTRICTS)
        if Farmer.query.filter_by(phone=phone).first():
            flash('Phone number already registered!', 'danger')
            return render_template('register.html', states=list(STATES_DISTRICTS.keys()), districts=STATES_DISTRICTS)
        farmer = Farmer(name=name, phone=phone, email=email,
                        password=generate_password_hash(password),
                        state=state, district=district)
        db.session.add(farmer)
        db.session.commit()
        login_user(farmer)
        flash(f'Welcome {name}! Please select your language.', 'success')
        return redirect(url_for('select_language'))
    return render_template('register.html', states=list(STATES_DISTRICTS.keys()), districts=STATES_DISTRICTS)

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        farmer = Farmer.query.filter_by(email=email).first()
        if farmer:
            token = generate_reset_token()
            farmer.reset_token = token
            farmer.reset_expiry = datetime.utcnow() + timedelta(hours=1)
            db.session.commit()
            reset_link = url_for('reset_password', token=token, _external=True)
            flash(f'Password reset link generated! In production this would be emailed. For demo: <a href="{reset_link}">Click here to reset</a>', 'info')
        else:
            flash('Email not found in our system.', 'danger')
    return render_template('forgot_password.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    farmer = Farmer.query.filter_by(reset_token=token).first()
    if not farmer or (farmer.reset_expiry and farmer.reset_expiry < datetime.utcnow()):
        flash('Invalid or expired reset link!', 'danger')
        return redirect(url_for('login'))
    if request.method == 'POST':
        new_password = request.form.get('password', '')
        if len(new_password) < 6:
            flash('Password must be at least 6 characters!', 'danger')
            return render_template('reset_password.html', token=token)
        farmer.password = generate_password_hash(new_password)
        farmer.reset_token = None
        farmer.reset_expiry = None
        db.session.commit()
        flash('Password reset successfully! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('reset_password.html', token=token)

@app.route('/select-language', methods=['GET', 'POST'])
@login_required
def select_language():
    if request.method == 'POST':
        lang = request.form.get('language', 'en')
        if lang not in ['en', 'hi', 'te']:
            lang = 'en'
        session['language'] = lang
        current_user.language = lang
        db.session.commit()
        return redirect(url_for('home'))
    return render_template('select_language.html')

@app.route('/set-language/<lang>')
@login_required
def set_language(lang):
    if lang in ['en', 'hi', 'te']:
        session['language'] = lang
        current_user.language = lang
        db.session.commit()
    return redirect(request.referrer or url_for('home'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('login'))

# ─────────────────────────────────────────────
# ROUTES - MAIN
# ─────────────────────────────────────────────
@app.route('/home')
@login_required
def home():
    lang = session.get('language', 'en')
    tips = QUICK_TIPS.get(lang, QUICK_TIPS['en'])
    tip = random.choice(tips)
    total_analyses = SoilAnalysis.query.filter_by(farmer_id=current_user.id).count()
    total_detections = DiseaseDetection.query.filter_by(farmer_id=current_user.id).count()
    recent_soil = SoilAnalysis.query.filter_by(farmer_id=current_user.id).order_by(SoilAnalysis.created_at.desc()).first()
    recent_disease = DiseaseDetection.query.filter_by(farmer_id=current_user.id).order_by(DiseaseDetection.created_at.desc()).first()
    market_prices = MarketPrice.query.order_by(MarketPrice.updated_at.desc()).limit(6).all()
    return render_template('home.html', tip=tip, total_analyses=total_analyses,
                           total_detections=total_detections, recent_soil=recent_soil,
                           recent_disease=recent_disease, market_prices=market_prices)

@app.route('/crop-ideas', methods=['GET', 'POST'])
@login_required
def crop_ideas():
    result = None
    if request.method == 'POST':
        state    = request.form.get('state', '')
        district = request.form.get('district', '')
        season   = request.form.get('season', '')
        acres    = float(request.form.get('acres', 1) or 1)
        image    = request.files.get('soil_image')

        if not image or not image.filename:
            flash('Please upload a soil image!', 'danger')
            return render_template('crop_ideas.html', result=None, states=list(STATES_DISTRICTS.keys()), districts=STATES_DISTRICTS)
        if not allowed_file(image.filename):
            flash(t('image_error'), 'danger')
            return render_template('crop_ideas.html', result=None, states=list(STATES_DISTRICTS.keys()), districts=STATES_DISTRICTS)

        filename = secure_filename(f"soil_{current_user.id}_{int(datetime.utcnow().timestamp())}.jpg")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image.save(filepath)

        soil_type = classify_soil(filepath)
        lang      = session.get('language', 'en')
        soil_info = SOIL_DATA[soil_type]

        # ── Weather Data ────────────────────────────────────────────
        season_key = season.lower().split()[0] if season else 'kharif'
        district_real_crops = DISTRICT_CROPS.get(district, {}).get(season_key, [])
        weather      = get_weather(state, district)           # pass district for accurate weather
        drought_mode = weather['drought_prob'] > 40
        # ── Crops with prices + profit + risk ───────────────────────
        crops_with_prices = {}
        for cat, items in soil_info['crops'].items():
            crops_with_prices[cat] = []
            for crop in items:
                # Try live Agmarknet price first, fall back to DB price
                live_price, live_demand = get_live_crop_price(crop['name'], state, district)
                db_price, db_demand     = get_market_prices(crop['name'], state)
                final_price  = live_price  or db_price
                final_demand = live_demand or db_demand
                is_live      = live_price is not None

                profit_data = get_profit_estimate(crop['name'], acres)
                risk        = get_risk_score(crop['name'], soil_type, season, weather)
                seasonal_ok = season.lower() in [s.lower() for s in CROP_DETAILS.get(crop['name'],{}).get('season',['kharif','rabi','zaid'])]
                crops_with_prices[cat].append({
                    'name'       : crop['name'],
                    'demand'     : final_demand or crop['demand'],
                    'price'      : (f"₹{final_price}/kg 🔴" if is_live
                                    else f"₹{final_price}/kg" if final_price
                                    else f"₹{crop['price']}/kg"),
                    'profit'     : profit_data,
                    'risk'       : risk,
                    'risk_label' : 'Low' if risk < 30 else ('Medium' if risk < 60 else 'High'),
                    'risk_color' : 'success' if risk < 30 else ('warning' if risk < 60 else 'danger'),
                    'water'      : CROP_DETAILS.get(crop['name'],{}).get('water','Medium'),
                    'seasonal_ok': seasonal_ok,
                    'drought_ok' : CROP_DETAILS.get(crop['name'],{}).get('drought_ok', False),
                    'calendar'   : FARMING_CALENDAR.get(crop['name'],{}).get(season.lower().split()[0] if season else 'kharif'),
                })

        # ── Soil Health Advice (language-aware) ─────────────────────
        _sha = SOIL_HEALTH_ADVICE.get(soil_type, {})
        def _lv(val, lg):
            return val.get(lg, val.get('en', val)) if isinstance(val, dict) else val
        soil_health = {
            'fertilizers' : _lv(_sha.get('fertilizers', []), lang),
            'organic'     : _lv(_sha.get('organic', []), lang),
            'green_manure': _lv(_sha.get('green_manure', ''), lang),
            'rotation'    : _lv(_sha.get('rotation', []), lang),
            'rotation_tip': _lv(_sha.get('rotation_tip', ''), lang),
        } if _sha else {}

        # ── Alternative Crops ───────────────────────────────────────
        alternatives = get_alternative_crops(soil_type, season, weather)

        # ── Success Story — real DB stories first ───────────────────
        story = None

        # Fetch ALL real stories — same district first, then same state
        state_districts = STATES_DISTRICTS.get(state, [])

        real_posts = CommunityPost.query.filter(
            CommunityPost.district.in_(state_districts)
        ).order_by(CommunityPost.likes.desc()).all()

        stories = []
        if real_posts:
            for rp in real_posts:
                if rp.farmer:
                    stories.append({
                        'crop'       : rp.crop,
                        'farmer_name': rp.farmer.name,
                        'body'       : rp.body,
                        'image_path' : rp.image_path,
                        'video_path' : getattr(rp, 'video_path', None),
                        'district'   : rp.district,
                        'likes'      : rp.likes,
                        'is_real'    : True,
                        'percent'    : 'Real Farmer',
                        'season'     : 'Kharif',
                        'profit'     : '',
                    })

        # Fallback to hardcoded if no real stories
        if not stories:
            state_stories = SUCCESS_STORIES.get(state, {})
            if district in state_stories:
                s = state_stories[district].copy()
                s['is_real'] = False
                stories.append(s)
            elif state_stories:
                s = list(state_stories.values())[0].copy()
                s['is_real'] = False
                stories.append(s)

        story = stories[0] if stories else None

        # ── Top recommended crop — always from district list ────────
        if district_real_crops:
            # Pick best crop from district list that has real data
            # Try each crop in priority order until we find one with data
            top_crop = None
            for candidate in district_real_crops:
                crop_info = CROP_DETAILS.get(candidate, {})
                if not crop_info:
                    continue  # skip if no data at all

                profit_data = get_profit_estimate(candidate, acres)
                risk        = get_risk_score(candidate, soil_type, season, weather)

                # Real water need from CROP_DETAILS
                water_need  = crop_info.get('water', 'Medium')

                # Real profit calculation
                if profit_data and profit_data['profit'] > 0:
                    top_crop = {
                        'name'       : candidate,
                        'profit'     : profit_data,
                        'risk'       : risk,
                        'risk_label' : 'Low' if risk < 30 else ('Medium' if risk < 60 else 'High'),
                        'risk_color' : 'success' if risk < 30 else ('warning' if risk < 60 else 'danger'),
                        'water'      : water_need,
                        'seasonal_ok': True,
                        'drought_ok' : crop_info.get('drought_ok', False),
                        'demand'     : 'high',
                        'price'      : f"₹{crop_info.get('price', 20)}/kg",
                        'calendar'   : FARMING_CALENDAR.get(candidate, {}).get(season_key),
                    }
                    break  # found a good crop, stop searching

            # If none of the district crops had data, use first one anyway
            if not top_crop:
                candidate   = district_real_crops[0]
                crop_info   = CROP_DETAILS.get(candidate, {})
                profit_data = get_profit_estimate(candidate, acres)
                risk        = get_risk_score(candidate, soil_type, season, weather)
                top_crop = {
                    'name'       : candidate,
                    'profit'     : profit_data,
                    'risk'       : risk,
                    'risk_label' : 'Low' if risk < 30 else ('Medium' if risk < 60 else 'High'),
                    'risk_color' : 'success' if risk < 30 else ('warning' if risk < 60 else 'danger'),
                    'water'      : crop_info.get('water', 'Medium'),
                    'seasonal_ok': True,
                    'drought_ok' : crop_info.get('drought_ok', False),
                    'demand'     : 'high',
                    'price'      : f"₹{crop_info.get('price', 20)}/kg",
                    'calendar'   : FARMING_CALENDAR.get(candidate, {}).get(season_key),
                }
        else:
            # No district data — fallback to profit+risk scoring
            all_crops_flat = [c for cat in crops_with_prices.values() for c in cat]
            def score(c):
                p = c['profit']['profit'] if c['profit'] else 0
                r = c['risk']
                s = 1 if c['seasonal_ok'] else 0
                return (p / 1000) - r + (s * 50)
            top_crop = max(all_crops_flat, key=score) if all_crops_flat else None

        # Add live prices to district crops
        district_crops_with_prices = []
        for dc in district_real_crops:
            lp, ld = get_live_crop_price(dc, state, district)
            db_p, db_d = get_market_prices(dc, state)
            final_p = lp or db_p or CROP_DETAILS.get(dc, {}).get('price')
            is_live_dc = lp is not None
            district_crops_with_prices.append({
                'name'    : dc,
                'price'   : final_p,
                'is_live' : is_live_dc,
                'demand'  : ld or db_d or 'medium',
            })

        result = {
            'district_crops': district_real_crops,
            'district_crops_prices': district_crops_with_prices,
            'soil_type'   : soil_type,
            'soil_type_display': translate_state(soil_type) if False else soil_type,  # kept for compat
            'state_display'   : translate_state(state),
            'district_display': translate_district(district),
            'features'    : soil_info['features'].get(lang, soil_info['features']['en']),
            'health_score': soil_info['health_score'],
            'nitrogen'    : soil_info['nitrogen'],
            'phosphorus'  : soil_info['phosphorus'],
            'potassium'   : soil_info['potassium'],
            'ph'          : soil_info['ph'],
            'recommendation': soil_info['recommendation'],
            'crops'       : crops_with_prices,
            'state'       : state,
            'district'    : district,
            'season'      : season,
            'acres'       : acres,
            'image'       : filename,
            'weather'     : weather,
            'drought_mode': drought_mode,
            'soil_health' : soil_health,
            'alternatives': alternatives,
            'story'       : story,
             'stories'    : stories,
            'top_crop'    : top_crop,
        }

        analysis = SoilAnalysis(
            farmer_id=current_user.id, soil_type=soil_type,
            state=state, district=district, season=season,
            image_path=filename, health_score=soil_info['health_score'],
            features=soil_info['features'].get('en'),
            result=json.dumps({k: v for k, v in result.items() if k not in ['weather','soil_health','crops']})
        )
        db.session.add(analysis)
        db.session.commit()
        result['analysis_id'] = analysis.id

    lang_now = session.get('language','en')
    st_display = STATES_DISPLAY.get(lang_now, STATES_DISPLAY['en'])
    dist_display = DISTRICTS_DISPLAY.get(lang_now, DISTRICTS_DISPLAY['en'])
    return render_template('crop_ideas.html', result=result,
                           states=list(STATES_DISTRICTS.keys()),
                           districts=STATES_DISTRICTS,
                           states_display=st_display,
                           districts_display=dist_display)

@app.route('/api/crop-compare')
@login_required
def crop_compare():
    crops  = request.args.get('crops', '').split(',')
    soil   = request.args.get('soil', 'Alluvial Soil')
    season = request.args.get('season', 'kharif')
    state  = request.args.get('state', 'Telangana')
    district = request.args.get('district', '')
    weather = get_weather(state, district)
    data = []
    season_key = season.lower().split()[0] if season else 'kharif'
    district_real_crops = DISTRICT_CROPS.get(district, {}).get(season_key, [])
    for c in crops[:6]:
        c = c.strip()
        p = get_profit_estimate(c, 1)
        r = get_risk_score(c, soil, season, weather)
        if p:
            data.append({
                'name'   : c,
                'cost'   : p['cost'],
                'revenue': p['revenue'],
                'profit' : p['profit'],
                'yield'  : p['yield_ton'],
                'water'  : p['water'],
                'risk'   : r,
                'risk_label': 'Low' if r<30 else ('Medium' if r<60 else 'High'),
            })
    return jsonify({'crops': data})

@app.route('/disease-prediction', methods=['GET', 'POST'])
@login_required
def disease_prediction():
    result = None
    if request.method == 'POST':
        image = request.files.get('leaf_image')
        if not image or not image.filename:
            flash('Please upload a leaf image!', 'danger')
            return render_template('disease_prediction.html', result=None)
        if not allowed_file(image.filename):
            flash(t('image_error'), 'danger')
            return render_template('disease_prediction.html', result=None)
        filename = secure_filename(f"leaf_{current_user.id}_{int(datetime.utcnow().timestamp())}.jpg")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image.save(filepath)
        disease_name = detect_plant_disease(filepath)
        lang = session.get('language', 'en')
        disease_info = DISEASES[disease_name]

        # Severity label + color
        severity = disease_info.get('severity', 'Moderate')
        severity_map = {
            'Mild':     {'color': 'success', 'icon': '🟢', 'pct': 30},
            'Moderate': {'color': 'warning', 'icon': '🟡', 'pct': 65},
            'Severe':   {'color': 'danger',  'icon': '🔴', 'pct': 90},
        }
        sev_info = severity_map.get(severity, severity_map['Moderate'])

        # WhatsApp message — safely handle dict or string fields
        _c = disease_info['cause']
        _cause_en = _c.get('en', list(_c.values())[0]) if isinstance(_c, dict) else str(_c)
        _t = disease_info['treatment']
        _treat_en = _t.get('en', list(_t.values())[0]) if isinstance(_t, dict) else str(_t)
        _p = disease_info['prevention']
        _prev_en = _p.get('en', list(_p.values())[0]) if isinstance(_p, dict) else str(_p)
        wa_text = (
            "🌿 *Disease Alert from Smart Agriculture App*\n\n"
            f"🔍 Detected: *{disease_name}*\n"
            f"⚠️ Severity: {severity}\n"
            f"🧫 Cause: {_cause_en}\n"
            f"💊 Treatment: {_treat_en[:150]}...\n"
            f"🛡️ Prevention: {_prev_en[:100]}...\n\n"
            "📱 Detected via Smart Agriculture App"
        )

        # Extract lang-aware fields
        cause_val = disease_info['cause']
        cause_str = cause_val.get(lang, cause_val.get('en', cause_val)) if isinstance(cause_val, dict) else cause_val
        organic_val = disease_info['organic']
        organic_str = organic_val.get(lang, organic_val.get('en', organic_val)) if isinstance(organic_val, dict) else organic_val
        prev_val = disease_info['prevention']
        prev_str = prev_val.get(lang, prev_val.get('en', prev_val)) if isinstance(prev_val, dict) else prev_val

        # Build translated spray schedule
        raw_schedule = disease_info.get('spray_schedule', [])
        t_schedule = []
        for step in raw_schedule:
            d = step['day']
            a = step['action']
            p = step['product']
            tm = step['time']
            t_schedule.append({
                'day'    : d.get(lang, d.get('en', d)) if isinstance(d, dict) else d,
                'action' : a.get(lang, a.get('en', a)) if isinstance(a, dict) else a,
                'product': p.get(lang, p.get('en', p)) if isinstance(p, dict) else p,
                'time'   : tm.get(lang, tm.get('en', tm)) if isinstance(tm, dict) else tm,
            })

        # Translated affected crops
        t_affected = [translate_crop(c) for c in disease_info.get('affected_crops', [])]
        # Translated disease name
        t_disease_name = translate_disease(disease_name)

        result = {
            'disease_name'   : t_disease_name,
            'disease_name_en': disease_name,
            'cause'          : cause_str,
            'treatment'      : disease_info['treatment'].get(lang, disease_info['treatment']['en']),
            'organic'        : organic_str,
            'prevention'     : prev_str,
            'confidence'     : disease_info['confidence'],
            'image'          : filename,
            'severity'       : severity,
            'severity_color' : sev_info['color'],
            'severity_icon'  : sev_info['icon'],
            'severity_pct'   : sev_info['pct'],
            'affected_crops' : t_affected,
            'treatment_cost' : disease_info.get('treatment_cost', {}),
            'spray_schedule' : t_schedule,
            'wa_text'        : wa_text,
        }
        # Helper: always extract English string before saving to SQLite DB
        def _en(val):
            if isinstance(val, dict): return val.get('en', list(val.values())[0])
            return str(val) if val else ''

        detection = DiseaseDetection(
            farmer_id=current_user.id, image_path=filename,
            disease_name=disease_name, confidence=disease_info['confidence'],
            cause          = _en(disease_info['cause']),
            treatment      = _en(disease_info['treatment']),
            organic_option = _en(disease_info['organic']),
            prevention     = _en(disease_info['prevention'])
        )
        db.session.add(detection)
        db.session.commit()
        result['detection_id'] = detection.id

    # Pass recent history
    history = DiseaseDetection.query.filter_by(farmer_id=current_user.id)              .order_by(DiseaseDetection.created_at.desc()).limit(5).all()
    return render_template('disease_prediction.html', result=result, history=history)

@app.route('/market')
@login_required
def market():
    lang = session.get('language','en')
    return render_template('market.html')

@app.route('/api/place_order', methods=['POST'])
@login_required
def api_place_order():
    data = request.get_json() or {}
    try:
        order = Order(
            farmer_id = current_user.id,
            order_id  = data.get('order_id','ORD'+str(int(datetime.utcnow().timestamp()))),
            items     = data.get('items',''),
            total     = float(data.get('total', 0)),
            payment   = data.get('payment',''),
            status    = 'Confirmed'
        )
        db.session.add(order)
        db.session.commit()
        return jsonify({'status':'ok','order_id':order.order_id})
    except Exception as e:
        db.session.rollback()
        app.logger.warning(f'Order save failed: {e}')
        return jsonify({'status':'ok','order_id':data.get('order_id','')})

@app.route('/schemes')
@login_required
def schemes():
    scheme_type = request.args.get('type', 'all')
    category = request.args.get('category', 'all')
    search = request.args.get('search', '').strip()
    query = GovernmentScheme.query.filter_by(is_active=True)
    if scheme_type != 'all':
        query = query.filter_by(scheme_type=scheme_type)
    if category != 'all':
        query = query.filter_by(category=category)
    if search:
        query = query.filter(GovernmentScheme.name.ilike(f'%{search}%'))
    all_schemes = query.all()
    categories = [c[0] for c in db.session.query(GovernmentScheme.category).distinct().all()]
    return render_template('schemes.html', schemes=all_schemes, categories=categories,
                           selected_type=scheme_type, selected_category=category, search=search)

@app.route('/schemes/<int:scheme_id>')
@login_required
def scheme_detail(scheme_id):
    scheme = GovernmentScheme.query.get_or_404(scheme_id)
    lang = session.get('language', 'en')
    if lang == 'hi' and scheme.description_hi:
        scheme.display_name = scheme.name_hi or scheme.name
        scheme.display_desc = scheme.description_hi
    elif lang == 'te' and scheme.description_te:
        scheme.display_name = scheme.name_te or scheme.name
        scheme.display_desc = scheme.description_te
    else:
        scheme.display_name = scheme.name
        scheme.display_desc = scheme.description
    return render_template('scheme_detail.html', scheme=scheme)

@app.route('/help', methods=['GET', 'POST'])
@login_required
def help_contact():
    if request.method == 'POST':
        msg = ContactMessage(
            farmer_id=current_user.id,
            name=request.form.get('name', ''),
            email=request.form.get('email', ''),
            subject=request.form.get('subject', 'General Query'),
            message=request.form.get('message', '')
        )
        db.session.add(msg)
        db.session.commit()
        flash('✅ Message sent successfully! We will respond within 24 hours.', 'success')
        return redirect(url_for('help_contact'))
    # Get current user's messages with replies
    user_messages = ContactMessage.query.filter_by(
        farmer_id=current_user.id
    ).order_by(ContactMessage.created_at.desc()).all()
    return render_template('help.html', user_messages=user_messages)

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'update_profile':
            current_user.name = request.form.get('name', current_user.name)
            current_user.phone = request.form.get('phone', current_user.phone)
            current_user.state = request.form.get('state', current_user.state)
            current_user.district = request.form.get('district', current_user.district)
            db.session.commit()
            flash('✅ Profile updated successfully!', 'success')
        elif action == 'change_password':
            old_pass = request.form.get('old_password')
            new_pass = request.form.get('new_password')
            if check_password_hash(current_user.password, old_pass):
                if len(new_pass) >= 6:
                    current_user.password = generate_password_hash(new_pass)
                    db.session.commit()
                    flash('✅ Password changed successfully!', 'success')
                else:
                    flash('New password must be at least 6 characters!', 'danger')
            else:
                flash('Current password is incorrect!', 'danger')
        elif action == 'upload_photo':
            photo = request.files.get('profile_photo')
            if photo and allowed_file(photo.filename):
                filename = secure_filename(f"profile_{current_user.id}.jpg")
                photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                current_user.profile_photo = filename
                db.session.commit()
                flash('✅ Profile photo updated!', 'success')
            else:
                flash(t('image_error'), 'danger')
        return redirect(url_for('profile'))
    analyses = SoilAnalysis.query.filter_by(farmer_id=current_user.id).order_by(SoilAnalysis.created_at.desc()).limit(5).all()
    detections = DiseaseDetection.query.filter_by(farmer_id=current_user.id).order_by(DiseaseDetection.created_at.desc()).limit(5).all()
    return render_template('profile.html', analyses=analyses, detections=detections,
                           states=list(STATES_DISTRICTS.keys()), districts=STATES_DISTRICTS)

# ─────────────────────────────────────────────
# PDF REPORT DOWNLOAD
# ─────────────────────────────────────────────
@app.route('/download-soil-report/<int:analysis_id>')
@login_required
def download_soil_report(analysis_id):
    analysis = SoilAnalysis.query.get_or_404(analysis_id)
    if analysis.farmer_id != current_user.id:
        flash('Unauthorized!', 'danger')
        return redirect(url_for('home'))
    result = json.loads(analysis.result) if analysis.result else {}
    html = f"""
    <html><head><style>
    body{{font-family:Arial,sans-serif;margin:40px;color:#333;}}
    .header{{background:#2d6a4f;color:white;padding:20px;border-radius:10px;margin-bottom:20px;}}
    .section{{background:#f5f9f5;border-left:4px solid #40916c;padding:15px;margin:15px 0;border-radius:5px;}}
    table{{width:100%;border-collapse:collapse;margin:10px 0;}}
    th{{background:#2d6a4f;color:white;padding:10px;text-align:left;}}
    td{{padding:8px;border-bottom:1px solid #ddd;}}
    .score{{font-size:2em;color:#2d6a4f;font-weight:bold;}}
    </style></head><body>
    <div class="header">
    <h1>🌾 Smart Agriculture - Soil Analysis Report</h1>
    <p>Farmer: {current_user.name} | Date: {analysis.created_at.strftime('%d %B %Y')}</p>
    <p>Location: {analysis.state}, {analysis.district} | Season: {analysis.season}</p>
    </div>
    <div class="section">
    <h2>Soil Analysis Result</h2>
    <p><strong>Soil Type:</strong> {analysis.soil_type}</p>
    <p><strong>Health Score:</strong> <span class="score">{analysis.health_score}/10</span></p>
    <p><strong>Features:</strong> {analysis.features}</p>
    </div>
    <div class="section">
    <h2>Nutrient Analysis</h2>
    <table>
    <tr><th>Parameter</th><th>Value</th><th>Status</th></tr>
    <tr><td>Nitrogen (N)</td><td>{result.get('nitrogen','N/A')}</td><td>{'✅ Good' if 'High' in str(result.get('nitrogen','')) else '⚠️ Needs attention'}</td></tr>
    <tr><td>Phosphorus (P)</td><td>{result.get('phosphorus','N/A')}</td><td>{'✅ Good' if 'High' in str(result.get('phosphorus','')) else '⚠️ Needs attention'}</td></tr>
    <tr><td>Potassium (K)</td><td>{result.get('potassium','N/A')}</td><td>{'✅ Good' if 'High' in str(result.get('potassium','')) else '⚠️ Needs attention'}</td></tr>
    <tr><td>pH Level</td><td>{result.get('ph','N/A')}</td><td>{'✅ Optimal' if 6<=float(result.get('ph',7))<=7.5 else '⚠️ Adjust needed'}</td></tr>
    </table>
    </div>
    <div class="section">
    <h2>Recommendations</h2>
    <p>{result.get('recommendation','Consult your local agriculture officer for specific recommendations.')}</p>
    </div>
    <div class="section">
    <h2>Recommended Crops</h2>
    <table><tr><th>Category</th><th>Crop</th><th>Market Demand</th><th>Price</th></tr>
    {''.join([f"<tr><td>{cat.title()}</td><td>{c['name']}</td><td>{c['demand'].title()}</td><td>{c['price']}</td></tr>" for cat,crops in result.get('crops',{{}}).items() for c in crops])}
    </table>
    </div>
    <p style="color:#888;font-size:0.8em;text-align:center;margin-top:30px;">
    Generated by Smart Agriculture System | {datetime.utcnow().strftime('%d %B %Y %H:%M')} | For guidance only
    </p>
    </body></html>
    """
    buffer = io.BytesIO()
    buffer.write(html.encode('utf-8'))
    buffer.seek(0)
    return send_file(buffer, as_attachment=True,
                     download_name=f"soil_report_{analysis_id}.html",
                     mimetype='text/html')

@app.route('/download-disease-report/<int:detection_id>')
@login_required
def download_disease_report(detection_id):
    detection = DiseaseDetection.query.get_or_404(detection_id)
    if detection.farmer_id != current_user.id:
        flash('Unauthorized!', 'danger')
        return redirect(url_for('home'))
    html = f"""
    <html><head><style>
    body{{font-family:Arial,sans-serif;margin:40px;color:#333;}}
    .header{{background:#c1121f;color:white;padding:20px;border-radius:10px;margin-bottom:20px;}}
    .section{{background:#fff5f5;border-left:4px solid #c1121f;padding:15px;margin:15px 0;border-radius:5px;}}
    .green{{background:#f5faf6;border-left-color:#40916c;}}
    .blue{{background:#f0f7ff;border-left-color:#0077b6;}}
    </style></head><body>
    <div class="header">
    <h1>🔬 Smart Agriculture - Disease Detection Report</h1>
    <p>Farmer: {current_user.name} | Date: {detection.created_at.strftime('%d %B %Y')}</p>
    </div>
    <div class="section">
    <h2>Disease Detected</h2>
    <p><strong>Disease Name:</strong> {detection.disease_name}</p>
    <p><strong>Cause:</strong> {detection.cause}</p>
    <p><strong>Confidence:</strong> {detection.confidence}%</p>
    </div>
    <div class="section">
    <h2>💊 Suggested Treatment</h2>
    <p>{detection.treatment}</p>
    </div>
    <div class="section green">
    <h2>🌿 Organic Option</h2>
    <p>{detection.organic_option}</p>
    </div>
    <div class="section blue">
    <h2>🛡️ Prevention Tips</h2>
    <p>{detection.prevention}</p>
    </div>
    <p style="color:#888;font-size:0.8em;text-align:center;margin-top:30px;">
    Generated by Smart Agriculture System | {datetime.utcnow().strftime('%d %B %Y %H:%M')} | Consult local agriculture officer for confirmation
    </p>
    </body></html>
    """
    buffer = io.BytesIO()
    buffer.write(html.encode('utf-8'))
    buffer.seek(0)
    return send_file(buffer, as_attachment=True,
                     download_name=f"disease_report_{detection_id}.html",
                     mimetype='text/html')

# ─────────────────────────────────────────────
# ADMIN ROUTES
# ─────────────────────────────────────────────
@app.route('/admin')
@login_required
def admin():
    if not current_user.is_admin:
        flash('Admin access required!', 'danger')
        return redirect(url_for('home'))
    farmers = Farmer.query.order_by(Farmer.created_at.desc()).all()
    messages = ContactMessage.query.order_by(ContactMessage.created_at.desc()).all()
    all_schemes = GovernmentScheme.query.all()
    total_analyses = SoilAnalysis.query.count()
    total_detections = DiseaseDetection.query.count()
    unread = ContactMessage.query.filter_by(is_read=False).count()
    farmer_stories = CommunityPost.query.order_by(
        CommunityPost.created_at.desc()).all()

    return render_template('admin.html', farmers=farmers, messages=messages,
                           schemes=all_schemes, total_analyses=total_analyses,
                           total_detections=total_detections, unread=unread,
                           farmer_stories=farmer_stories,
                           districts=STATES_DISTRICTS)
@app.route('/admin/mark-read/<int:msg_id>')
@login_required
def mark_read(msg_id):
    if not current_user.is_admin:
        return redirect(url_for('home'))
    msg = ContactMessage.query.get_or_404(msg_id)
    msg.is_read = True
    db.session.commit()
    return redirect(url_for('admin'))

@app.route('/admin/reply/<int:msg_id>', methods=['POST'])
@login_required
def reply_message(msg_id):
    if not current_user.is_admin:
        return redirect(url_for('home'))
    msg = ContactMessage.query.get_or_404(msg_id)
    msg.reply = request.form.get('reply', '')
    msg.is_read = True
    db.session.commit()
    # Send email notification to farmer
    farmer = Farmer.query.get(msg.farmer_id)
    if farmer and farmer.email and MAIL_USERNAME:
        threading.Thread(
            target=send_reply_email,
            args=(farmer.name, farmer.email, msg.subject, msg.message, msg.reply)
        ).start()
        flash('✅ Reply sent! Email notification sent to farmer.', 'success')
    else:
        flash('✅ Reply sent!', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/add-scheme', methods=['POST'])
@login_required
def add_scheme():
    if not current_user.is_admin:
        return redirect(url_for('home'))
    scheme = GovernmentScheme(
        name=request.form.get('name'),
        name_hi=request.form.get('name_hi'),
        name_te=request.form.get('name_te'),
        scheme_type=request.form.get('scheme_type'),
        category=request.form.get('category'),
        state=request.form.get('state', 'All'),
        description=request.form.get('description'),
        description_hi=request.form.get('description_hi'),
        description_te=request.form.get('description_te'),
        benefit=request.form.get('benefit'),
        eligibility=request.form.get('eligibility'),
        how_to_apply=request.form.get('how_to_apply'),
        documents=request.form.get('documents'),
        official_link=request.form.get('official_link'),
        last_date=request.form.get('last_date')
    )
    db.session.add(scheme)
    db.session.commit()
    flash('✅ Scheme added successfully!', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/update-price', methods=['POST'])
@login_required
def update_price():
    if not current_user.is_admin:
        return redirect(url_for('home'))
    crop = request.form.get('crop_name')
    price = float(request.form.get('price', 0))
    demand = request.form.get('demand', 'medium')
    state = request.form.get('state', 'All')
    existing = MarketPrice.query.filter_by(crop_name=crop, state=state).first()
    if existing:
        existing.price_per_kg = price
        existing.demand = demand
        existing.updated_at = datetime.utcnow()
    else:
        db.session.add(MarketPrice(crop_name=crop, price_per_kg=price, demand=demand, state=state))
    db.session.commit()
    flash(f'✅ Price for {crop} updated!', 'success')
    return redirect(url_for('admin'))
@app.route('/admin/add-story', methods=['POST'])
@login_required
def admin_add_story():
    if not current_user.is_admin:
        return redirect(url_for('home'))

    farmer_name = request.form.get('farmer_name', '')
    district    = request.form.get('district', '')
    crop        = request.form.get('crop', '')
    acres       = request.form.get('acres', '')
    profit      = request.form.get('profit', '')
    season      = request.form.get('season', 'Kharif')
    story_text  = request.form.get('story', '')
    likes       = int(request.form.get('likes', 25))

    if not story_text:
        story_text = (
            f"{district}లో {acres} ఎకరాల {crop} సాగు చేశాను. "
            f"ఈ {season} సీజన్‌లో {profit} లాభం వచ్చింది. "
            f"స్మార్ట్ అగ్రికల్చర్ యాప్ చాలా సహాయపడింది."
        )

    image_path = None
    photo = request.files.get('farmer_photo')
    if photo and photo.filename and allowed_file(photo.filename):
        filename = secure_filename(
            f"story_{district}_{crop}_{int(datetime.utcnow().timestamp())}.jpg"
        )
        photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        image_path = filename

    video_path = None
    video = request.files.get('farmer_video')
    if video and video.filename:
        ext = video.filename.rsplit('.', 1)[-1].lower()
        if ext in {'mp4', 'mov', 'avi', 'webm'}:
            vfilename = secure_filename(
                f"story_video_{district}_{crop}_{int(datetime.utcnow().timestamp())}.{ext}"
            )
            video.save(os.path.join(app.config['UPLOAD_FOLDER'], vfilename))
            video_path = vfilename

    email = f"{farmer_name.lower().replace(' ', '.')}@family.farm"
    farmer = Farmer.query.filter_by(email=email).first()
    if not farmer:
        farmer = Farmer(
            name     = farmer_name,
            phone    = f"90000{int(datetime.utcnow().timestamp()) % 100000:05d}",
            email    = email,
            password = generate_password_hash("farm2024"),
            state    = "Telangana",
            district = district,
            language = "te"
        )
        db.session.add(farmer)
        db.session.flush()

    post = CommunityPost(
        farmer_id  = farmer.id,
        title      = f"{crop} సాగులో విజయం — {district}",
        body       = story_text,
        crop       = crop,
        district   = district,
        image_path = image_path,
        video_path = video_path,
        likes      = likes
    )
    db.session.add(post)
    db.session.commit()

    flash(f'✅ Story for {farmer_name} added successfully!', 'success')
    return redirect(url_for('admin'))


@app.route('/admin/delete-story/<int:story_id>')
@login_required
def admin_delete_story(story_id):
    if not current_user.is_admin:
        return redirect(url_for('home'))
    post = CommunityPost.query.get_or_404(story_id)
    db.session.delete(post)
    db.session.commit()
    flash('✅ Story deleted!', 'success')
    return redirect(url_for('admin'))

# ─────────────────────────────────────────────
# API
# ─────────────────────────────────────────────
@app.route('/api/districts/<state>')
def get_districts(state):
    return jsonify(STATES_DISTRICTS.get(state, []))

@app.route('/api/market-prices')
@login_required
def api_market_prices():
    prices = MarketPrice.query.all()
    return jsonify([{'crop': p.crop_name, 'price': p.price_per_kg, 'demand': p.demand} for p in prices])

@app.route('/api/mandi-prices/<crop>/<state>/<district>')
@login_required
def api_mandi_prices(crop, state, district):
    mandis = get_mandi_prices_for_district(crop, state, district)
    return jsonify({
        'crop'    : crop,
        'state'   : state,
        'district': district,
        'mandis'  : mandis,
        'count'   : len(mandis),
    })
    
@app.route('/api/nearest-mandis/<district>/<state>')
@login_required
def api_nearest_mandis(district, state):
    crop   = request.args.get('crop', None)
    mandis = get_live_nearest_mandis(district, state, crop)
    return jsonify({
        'district'   : district,
        'state'      : state,
        'crop'       : crop,
        'mandis'     : mandis,
        'count'      : len(mandis),
        'live_count' : sum(1 for m in mandis if m['is_live']),
        'geocoded'   : sum(1 for m in mandis if m['lat'] is not None),
    })
@app.route('/api/weather/<state>/<district>')   
@login_required
def api_weather_district(state, district):
    data = get_weather(state, district)
    return jsonify(data)

@app.route('/api/weather/<state>')              
@login_required
def api_weather_state(state):
    data = get_weather(state)
    return jsonify(data)

@app.route('/farm-weather')                     
@login_required
def farm_weather():
    return render_template(
        'farm_weather_monitor.html',
        states=list(STATES_DISTRICTS.keys()),
        districts=STATES_DISTRICTS
    )

      

# ─────────────────────────────────────────────
# DATABASE SEED
# ─────────────────────────────────────────────
def seed_database():
    if GovernmentScheme.query.count() == 0:
        schemes = [
            GovernmentScheme(name="PM Kisan Samman Nidhi", name_hi="पीएम किसान सम्मान निधि", name_te="పీఎం కిసాన్ సమ్మాన్ నిధి",
                scheme_type="central", category="Financial Aid", state="All",
                description="Financial support of ₹6000 per year to all farmer families across India, paid in 3 instalments of ₹2000 directly to bank accounts.",
                description_hi="भारत भर में सभी किसान परिवारों को प्रति वर्ष ₹6000 की वित्तीय सहायता, ₹2000 की 3 किश्तों में सीधे बैंक खातों में।",
                description_te="భారతదేశంలోని అన్ని రైతు కుటుంబాలకు సంవత్సరానికి ₹6000, నేరుగా బ్యాంక్ ఖాతాలకు ₹2000 చొప్పున 3 వాయిదాలలో.",
                benefit="₹6,000 per year (3 instalments of ₹2,000)", eligibility="All land-holding farmer families in India",
                how_to_apply="Visit pmkisan.gov.in or nearest CSC center. Submit Aadhaar, bank passbook and land records.",
                documents="Aadhaar Card, Bank Passbook, Land Records, Mobile Number", official_link="https://pmkisan.gov.in", last_date="Ongoing"),
            GovernmentScheme(name="PM Fasal Bima Yojana", name_hi="प्रधानमंत्री फसल बीमा योजना", name_te="ప్రధానమంత్రి ఫసల్ బీమా యోజన",
                scheme_type="central", category="Crop Insurance", state="All",
                description="Comprehensive crop insurance providing financial support for crop loss due to natural calamities, pests and diseases. Premium as low as 2% for Kharif crops.",
                description_hi="प्राकृतिक आपदाओं, कीटों और बीमारियों के कारण फसल हानि के लिए व्यापक बीमा। खरीफ फसलों के लिए केवल 2% प्रीमियम।",
                description_te="సహజ విపత్తులు, తెగుళ్ళు మరియు వ్యాధుల కారణంగా పంట నష్టానికి సమగ్ర బీమా. ఖరీఫ్ పంటలకు కేవలం 2% ప్రీమియం.",
                benefit="Up to ₹2 lakh compensation. Premium: 2% Kharif, 1.5% Rabi", eligibility="All farmers growing notified crops",
                how_to_apply="Apply at nearest bank branch or pmfby.gov.in before sowing season.",
                documents="Land records, Bank account, Aadhaar, Sowing certificate", official_link="https://pmfby.gov.in", last_date="Before each sowing season"),
            GovernmentScheme(name="Kisan Credit Card (KCC)", name_hi="किसान क्रेडिट कार्ड", name_te="కిసాన్ క్రెడిట్ కార్డ్",
                scheme_type="central", category="Loans & Credit", state="All",
                description="Provides farmers affordable credit for agriculture and allied activities at 4% interest rate per annum for loans up to ₹3 lakh with timely repayment.",
                description_hi="कृषि गतिविधियों के लिए किसानों को किफायती ऋण, समय पर चुकाने पर ₹3 लाख तक 4% ब्याज दर पर।",
                description_te="వ్యవసాయ కార్యకలాపాలకు రైతులకు సాధ్యమైనంత తక్కువ వడ్డీకి రుణం, సకాలంలో చెల్లింపుతో ₹3 లక్షల వరకు 4% వడ్డీ.",
                benefit="Loan up to ₹3 lakh at 4% interest rate", eligibility="All farmers, sharecroppers, SHGs",
                how_to_apply="Apply at nearest bank branch with land documents.",
                documents="Aadhaar, Land records, Passport photo, Bank account", official_link="https://www.nabard.org", last_date="Ongoing"),
            GovernmentScheme(name="Soil Health Card Scheme", name_hi="मृदा स्वास्थ्य कार्ड योजना", name_te="మృదా ఆరోగ్య కార్డ్ పథకం",
                scheme_type="central", category="Soil Testing", state="All",
                description="Free soil testing for farmers providing information on soil nutrient status and recommendations on appropriate fertilizer dosage for better yield.",
                description_hi="किसानों के लिए मुफ्त मृदा परीक्षण, मिट्टी पोषक तत्व की स्थिति और उचित उर्वरक खुराक पर सिफारिशें।",
                description_te="రైతులకు ఉచిత మట్టి పరీక్ష, మట్టి పోషక స్థితిపై సమాచారం మరియు సరైన ఎరువుల మోతాదుపై సిఫార్సులు.",
                benefit="Free soil testing, Personalized fertilizer recommendations", eligibility="All farmers in India",
                how_to_apply="Contact nearest agriculture department or Krishi Vigyan Kendra.",
                documents="Aadhaar card, Land details", official_link="https://soilhealth.dac.gov.in", last_date="Ongoing"),
            GovernmentScheme(name="PM Krishi Sinchai Yojana", name_hi="प्रधानमंत्री कृषि सिंचाई योजना", name_te="ప్రధానమంత్రి కృషి సించాయ్ యోజన",
                scheme_type="central", category="Water & Irrigation", state="All",
                description="Ensures access to protective irrigation to all agricultural farms to produce more crops per drop of water. 55% subsidy on drip/sprinkler systems for small farmers.",
                description_hi="सभी कृषि खेतों को सुरक्षात्मक सिंचाई की पहुंच सुनिश्चित करता है। छोटे किसानों के लिए ड्रिप/स्प्रिंकलर सिस्टम पर 55% सब्सिडी।",
                description_te="అన్ని వ్యవసాయ పొలాలకు రక్షిత సేద్యపు నీటి సదుపాయం. చిన్న రైతులకు డ్రిప్/స్ప్రింక్లర్ వ్యవస్థలపై 55% సబ్సిడీ.",
                benefit="55% subsidy on drip/sprinkler irrigation for small farmers", eligibility="All farmers, higher subsidy for small/marginal farmers",
                how_to_apply="Apply through state agriculture department or online portal.",
                documents="Land records, Aadhaar, Bank account", official_link="https://pmksy.gov.in", last_date="Ongoing"),
            GovernmentScheme(name="PM Kisan Mandhan Yojana", name_hi="पीएम किसान मानधन योजना", name_te="పీఎం కిసాన్ మాన్ ధన్ యోజన",
                scheme_type="central", category="Pension", state="All",
                description="Pension scheme for small and marginal farmers ensuring ₹3000 monthly pension after attaining age of 60 years. Minimal monthly contribution of ₹55-200.",
                description_hi="छोटे किसानों के लिए पेंशन योजना, 60 वर्ष के बाद ₹3000 मासिक पेंशन। ₹55-200 की न्यूनतम मासिक योगदान।",
                description_te="చిన్న రైతులకు పెన్షన్ పథకం, 60 సంవత్సరాల తర్వాత నెలకు ₹3000. నెలకు ₹55-200 చిన్న విరాళం.",
                benefit="₹3,000 monthly pension after age 60", eligibility="Small/marginal farmers aged 18-40 with up to 2 hectares land",
                how_to_apply="Apply at nearest CSC center with land documents and Aadhaar.",
                documents="Aadhaar, Land records, Bank passbook, Mobile number", official_link="https://maandhan.in", last_date="Ongoing"),
            GovernmentScheme(name="eNAM - National Agriculture Market", name_hi="eNAM - राष्ट्रीय कृषि बाजार", name_te="eNAM - జాతీయ వ్యవసాయ మార్కెట్",
                scheme_type="central", category="Market Access", state="All",
                description="Online trading platform for agricultural commodities allowing farmers to sell produce online to get best market price across India without middlemen.",
                description_hi="कृषि वस्तुओं के लिए ऑनलाइन ट्रेडिंग प्लेटफॉर्म, बिचौलियों के बिना पूरे भारत में सर्वोत्तम मूल्य पाने के लिए।",
                description_te="వ్యవసాయ వస్తువుల కోసం ఆన్‌లైన్ వ్యాపార వేదిక, దళారులు లేకుండా భారతదేశం అంతటా అత్యుత్తమ ధర పొందేందుకు.",
                benefit="Better price realization, transparent trading, no middlemen", eligibility="All farmers with produce to sell",
                how_to_apply="Register at enam.gov.in or visit nearest APMC market.",
                documents="Aadhaar, Bank account, Mobile number", official_link="https://enam.gov.in", last_date="Ongoing"),
            GovernmentScheme(name="Paramparagat Krishi Vikas Yojana", name_hi="परम्परागत कृषि विकास योजना", name_te="పరంపరాగత కృషి వికాస యోజన",
                scheme_type="central", category="Organic Farming", state="All",
                description="Promotes organic farming through cluster approach. Provides ₹50,000/hectare for 3 years including organic certification support and market linkage.",
                description_hi="क्लस्टर दृष्टिकोण के माध्यम से जैविक खेती को बढ़ावा। 3 वर्षों के लिए ₹50,000/हेक्टेयर और जैविक प्रमाणन सहायता।",
                description_te="క్లస్టర్ విధానం ద్వారా సేంద్రీయ వ్యవసాయాన్ని ప్రోత్సహిస్తుంది. 3 సంవత్సరాలకు ₹50,000/హెక్టార్ మరియు సేంద్రీయ ధృవీకరణ మద్దతు.",
                benefit="₹50,000 per hectare for 3 years, organic certification support", eligibility="Group of minimum 50 farmers willing to adopt organic farming",
                how_to_apply="Contact nearest Krishi Vigyan Kendra or agriculture department.",
                documents="Aadhaar, Land records, Group formation certificate", official_link="https://pgsindia-ncof.gov.in", last_date="Ongoing"),
            GovernmentScheme(name="Rythu Bandhu Scheme", name_hi="रैतू बंधु योजना", name_te="రైతు బంధు పథకం",
                scheme_type="state", category="Financial Aid", state="Telangana",
                description="Telangana government's investment support providing ₹10,000 per acre per season to all farmer landowners for agricultural investment needs.",
                description_hi="तेलंगाना सरकार की निवेश सहायता योजना, सभी किसान भूमि मालिकों को प्रति एकड़ प्रति सीजन ₹10,000।",
                description_te="తెలంగాణ ప్రభుత్వ పెట్టుబడి మద్దతు పథకం, అన్ని రైతు భూమి యజమానులకు సీజన్‌కు ఎకరాకు ₹10,000.",
                benefit="₹10,000 per acre per season (Kharif & Rabi)", eligibility="All farmer landowners in Telangana",
                how_to_apply="Automatic enrollment based on land records. Visit agriculture office if not enrolled.",
                documents="Passbook/Pattadar Passbook, Aadhaar, Bank account linked to Aadhaar", official_link="https://rythubharosa.telangana.gov.in/", last_date="Each season"),
            GovernmentScheme(name="Rythu Bima", name_hi="रैतू बीमा", name_te="రైతు బీమా",
                scheme_type="state", category="Life Insurance", state="Telangana",
                description="Life insurance for Telangana farmers providing ₹5 lakh insurance coverage to farmer families in case of farmer's death. Premium paid by state government.",
                description_hi="तेलंगाना किसानों के लिए जीवन बीमा, किसान की मृत्यु पर परिवार को ₹5 लाख बीमा। प्रीमियम राज्य सरकार द्वारा।",
                description_te="తెలంగాణ రైతులకు జీవిత బీమా, రైతు మరణించినప్పుడు కుటుంబానికి ₹5 లక్షల బీమా. ప్రీమియం రాష్ట్ర ప్రభుత్వం చెల్లిస్తుంది.",
                benefit="₹5 lakh life insurance coverage, premium paid by government", eligibility="All Rythu Bandhu beneficiaries aged 18-59 in Telangana",
                how_to_apply="Automatic enrollment for Rythu Bandhu beneficiaries.",
                documents="Rythu Bandhu passbook, Aadhaar card", official_link="https://www.myscheme.gov.in/schemes/rythu-bima", last_date="Ongoing"),
        ]
        for s in schemes:
            db.session.add(s)

    if MarketPrice.query.count() == 0:
        prices = [
            MarketPrice(crop_name="Tomato", price_per_kg=25.0, demand="high", state="All"),
            MarketPrice(crop_name="Onion", price_per_kg=30.0, demand="high", state="All"),
            MarketPrice(crop_name="Potato", price_per_kg=20.0, demand="high", state="All"),
            MarketPrice(crop_name="Chilli", price_per_kg=40.0, demand="high", state="All"),
            MarketPrice(crop_name="Mango", price_per_kg=60.0, demand="high", state="All"),
            MarketPrice(crop_name="Banana", price_per_kg=35.0, demand="high", state="All"),
            MarketPrice(crop_name="Rice", price_per_kg=35.0, demand="high", state="All"),
            MarketPrice(crop_name="Wheat", price_per_kg=22.0, demand="high", state="All"),
            MarketPrice(crop_name="Maize", price_per_kg=20.0, demand="medium", state="All"),
            MarketPrice(crop_name="Groundnut", price_per_kg=55.0, demand="high", state="All"),
            MarketPrice(crop_name="Marigold", price_per_kg=20.0, demand="high", state="All"),
            MarketPrice(crop_name="Rose", price_per_kg=80.0, demand="high", state="All"),
        ]
        for p in prices:
            db.session.add(p)

    if Farmer.query.count() == 0:
        admin_farmer = Farmer(
            name="Admin Farmer", phone="9999999999", email="admin@farm.com",
            password=generate_password_hash("password123"),
            state="Telangana", district="Warangal",
            language="en", is_admin=True
        )
        db.session.add(admin_farmer)

    db.session.commit()

with app.app_context():
    db.create_all()
    seed_database()
    # Pre-load soil model at startup so first prediction is fast
    print('🚀 Loading CNN models...')
    load_soil_model()
    load_disease_model()

@app.route('/api/model-status')
def model_status():
    """Check if CNN models are loaded — visit /api/model-status in browser to verify"""
    soil_path    = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models', 'soil_model.h5')
    disease_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models', 'disease_model.h5')
    return jsonify({
        'soil_model_loaded'   : SOIL_MODEL is not None,
        'disease_model_loaded': DISEASE_MODEL is not None,
        'soil_model_file_exists'   : os.path.exists(soil_path),
        'disease_model_file_exists': os.path.exists(disease_path),
        'soil_classes'   : SOIL_CLASSES,
        'disease_classes': DISEASE_CLASSES,
    })



@app.route('/api/submit_query', methods=['POST'])
def api_submit_query():
    """Receive farmer query and save to DB / send notification"""
    data = request.get_json() or {}
    name     = data.get('name', 'Unknown')
    phone    = data.get('phone', '')
    message  = data.get('message', '')
    category = data.get('category', 'General')
    soil     = data.get('soil', '')
    location = data.get('location', '')
    season   = data.get('season', '')
    if not message:
        return jsonify({'status': 'error', 'msg': 'Empty message'}), 400
    # Save as help message in DB
    try:
        from datetime import datetime
        msg_obj = HelpMessage(
            name=name,
            email=f'{phone}@farmer.query',
            subject=f'[{category}] Query from {location} — {soil}',
            message=f'Phone: {phone}\nSoil: {soil}\nLocation: {location}\nSeason: {season}\n\n{message}',
            created_at=datetime.utcnow()
        )
        db.session.add(msg_obj)
        db.session.commit()
    except Exception as e:
        app.logger.warning(f'submit_query DB save failed: {e}')
    return jsonify({'status': 'ok', 'message': 'Query received'})

@app.route('/api/chat', methods=['POST'])
@login_required
def api_chat():
    data    = request.get_json()
    message = data.get('message','').strip()
    context = data.get('context','')
    lang    = session.get('language','en')

    # Simple rule-based farming chatbot
    msg = message.lower()
    replies = {
        'fertilizer': {
            'en': '🌱 For best results, use NPK 17:17:17 as base dose. Apply Urea in split doses — at sowing, tillering and panicle initiation stages. Always do soil testing first for precise dosage.',
            'hi': '🌱 NPK 17:17:17 आधार खुराक के रूप में उपयोग करें। यूरिया को बुवाई, कल्ले निकलने और बाली निकलने पर विभाजित करें।',
            'te': '🌱 NPK 17:17:17 బేస్ డోస్ గా వాడండి. యూరియాను విత్తనాల సమయం, పిలకలు, పుష్పించే దశలలో విభజించి వేయండి.'
        },
        'water': {
            'en': '💧 Water management tip: Use drip irrigation to save 40% water. Water in early morning (6-8 AM) to reduce evaporation. Check soil moisture before every irrigation.',
            'hi': '💧 ड्रिप सिंचाई से 40% पानी बचाएं। सुबह 6-8 बजे सिंचाई करें।',
            'te': '💧 డ్రిప్ నీటిపారుదలతో 40% నీరు ఆదా చేయండి. ఉదయం 6-8 గంటలకు నీరు పెట్టండి.'
        },
        'pest': {
            'en': '🦟 Pest control: Use Neem oil spray (5ml/litre) as organic option. For severe infestation use recommended pesticides. Always spray in evening to protect bees.',
            'hi': '🦟 जैविक नियंत्रण के लिए नीम तेल स्प्रे (5ml/लीटर) उपयोग करें।',
            'te': '🦟 సేంద్రీయ నివారణకు వేప నూనె స్ప్రే (5ml/లీటర్) వాడండి.'
        },
        'sow': {
            'en': '📅 Sowing timing is critical. Kharif crops: June-July. Rabi crops: October-November. Zaid crops: February-March. Always check local weather before sowing.',
            'hi': '📅 खरीफ: जून-जुलाई। रबी: अक्टूबर-नवंबर। जायद: फरवरी-मार्च।',
            'te': '📅 ఖరీఫ్: జూన్-జులై. రబీ: అక్టోబర్-నవంబర్. జైద్: ఫిబ్రవరి-మార్చి.'
        },
        'soil': {
            'en': '🌍 Soil improvement: Add 4-5 tons of FYM (Farm Yard Manure) per acre every year. Practice crop rotation. Test soil every 2 years. Green manuring improves nitrogen naturally.',
            'hi': '🌍 प्रति एकड़ 4-5 टन गोबर खाद डालें। फसल चक्र अपनाएं। हर 2 साल में मृदा परीक्षण करें।',
            'te': '🌍 ఎకరాకు 4-5 టన్నుల పశువుల ఎరువు వేయండి. పంట మార్పిడి చేయండి. 2 సంవత్సరాలకు ఒకసారి మట్టి పరీక్ష చేయించండి.'
        },
    }

    reply_key = 'en'
    if lang in ['hi','te']: reply_key = lang

    for key, texts in replies.items():
        if key in msg:
            return jsonify({'reply': texts.get(reply_key, texts['en'])})

    # Default reply
    default = {
        'en': f'🌱 For farming advice specific to your soil and region, I recommend: (1) Contact your local Krishi Vigyan Kendra, (2) Call Kisan helpline 1800-180-1551, (3) Check the crop calendar above for timing. Your context: {context}',
        'hi': f'🌱 स्थानीय कृषि विज्ञान केंद्र से संपर्क करें या किसान हेल्पलाइन 1800-180-1551 पर कॉल करें।',
        'te': f'🌱 స్థానిక కృషి విజ్ఞాన కేంద్రాన్ని సంప్రదించండి లేదా కిసాన్ హెల్ప్ లైన్ 1800-180-1551 కి కాల్ చేయండి.'
    }
    return jsonify({'reply': default.get(lang, default['en'])})

@app.route('/crop-calendar/<int:analysis_id>/<crop>/<season>')
@login_required
def generate_crop_calendar(analysis_id, crop, season):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib import colors
        import io

        cal = FARMING_CALENDAR.get(crop, {}).get(season.lower(), {})
        if not cal:
            flash(f'Calendar not available for {crop} in {season} season.', 'warning')
            return redirect(url_for('crop_ideas'))

        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=40, bottomMargin=40)
        styles = getSampleStyleSheet()
        elements = []

        elements.append(Paragraph(f"🗓️ Farming Calendar — {crop}", styles['Title']))
        elements.append(Paragraph(f"Season: {season.capitalize()} | Generated for Smart Agriculture App", styles['Normal']))
        elements.append(Spacer(1, 20))

        data = [['Activity', 'Date / Schedule']]
        for k, v in cal.items():
            data.append([k.replace('_',' ').capitalize(), v])

        t = Table(data, colWidths=[200, 280])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2d6a4f')),
            ('TEXTCOLOR',  (0,0), (-1,0), colors.white),
            ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE',   (0,0), (-1,0), 12),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#f0fff4'), colors.white]),
            ('FONTSIZE',   (0,1), (-1,-1), 11),
            ('GRID',       (0,0), (-1,-1), 0.5, colors.HexColor('#b7e4c7')),
            ('PADDING',    (0,0), (-1,-1), 10),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 20))
        elements.append(Paragraph("💡 Tip: Always consult your local Krishi Vigyan Kendra for region-specific advice.", styles['Normal']))

        doc.build(elements)
        buf.seek(0)
        return send_file(buf, as_attachment=True, download_name=f'{crop}_calendar_{season}.pdf', mimetype='application/pdf')

    except ImportError:
        flash('PDF generation requires reportlab. Run: pip install reportlab', 'warning')
        return redirect(url_for('crop_ideas'))
    except Exception as e:
        flash(f'Calendar generation error: {e}', 'danger')
        return redirect(url_for('crop_ideas'))

@app.route('/disease-report/<int:detection_id>')
@login_required
def generate_disease_report(detection_id):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        import io

        det = DiseaseDetection.query.get_or_404(detection_id)
        disease_info = DISEASES.get(det.disease_name, {})

        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=40, bottomMargin=40, leftMargin=50, rightMargin=50)
        styles = getSampleStyleSheet()
        elements = []

        elements.append(Paragraph(f"Disease Detection Report", styles['Title']))
        elements.append(Paragraph(f"Smart Agriculture App — {det.created_at.strftime('%d %B %Y')}", styles['Normal']))
        elements.append(Spacer(1, 16))

        info_data = [
            ['Disease Detected', det.disease_name],
            ['Severity', disease_info.get('severity','Moderate')],
            ['AI Confidence', f"{det.confidence}%"],
            ['Cause', det.cause],
            ['Treatment Cost', f"₹{disease_info.get('treatment_cost',{}).get('min','—')}–{disease_info.get('treatment_cost',{}).get('max','—')} per acre"],
        ]
        t = Table(info_data, colWidths=[160, 310])
        t.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(0,-1), colors.HexColor('#7b2d8b')),
            ('TEXTCOLOR',(0,0),(0,-1), colors.white),
            ('FONTNAME',(0,0),(-1,-1),'Helvetica'),
            ('FONTSIZE',(0,0),(-1,-1),10),
            ('ROWBACKGROUNDS',(1,0),(1,-1),[colors.HexColor('#fdf6ff'), colors.white]),
            ('GRID',(0,0),(-1,-1),0.5, colors.HexColor('#e1bee7')),
            ('PADDING',(0,0),(-1,-1),10),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 16))

        elements.append(Paragraph("Treatment", styles['Heading2']))
        elements.append(Paragraph(det.treatment or '—', styles['Normal']))
        elements.append(Spacer(1, 10))
        elements.append(Paragraph("Organic Option", styles['Heading2']))
        elements.append(Paragraph(det.organic_option or '—', styles['Normal']))
        elements.append(Spacer(1, 10))
        elements.append(Paragraph("Prevention", styles['Heading2']))
        elements.append(Paragraph(det.prevention or '—', styles['Normal']))
        elements.append(Spacer(1, 16))

        spray = disease_info.get('spray_schedule', [])
        if spray:
            elements.append(Paragraph("Day-by-Day Spray Schedule", styles['Heading2']))
            sdata = [['Day','Action','Product','Time']]
            for s in spray:
                sdata.append([s['day'], s['action'], s['product'], s['time']])
            st = Table(sdata, colWidths=[55,170,170,45])
            st.setStyle(TableStyle([
                ('BACKGROUND',(0,0),(-1,0), colors.HexColor('#7b2d8b')),
                ('TEXTCOLOR',(0,0),(-1,0), colors.white),
                ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),
                ('FONTSIZE',(0,0),(-1,-1),8),
                ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.HexColor('#fdf6ff'), colors.white]),
                ('GRID',(0,0),(-1,-1),0.5, colors.HexColor('#e1bee7')),
                ('PADDING',(0,0),(-1,-1),7),
            ]))
            elements.append(st)

        doc.build(elements)
        buf.seek(0)
        return send_file(buf, as_attachment=True,
                        download_name=f'disease_report_{det.disease_name.replace(" ","_")}.pdf',
                        mimetype='application/pdf')
    except ImportError:
        flash('PDF needs reportlab. Run: pip install reportlab', 'warning')
        return redirect(url_for('disease_prediction'))
    except Exception as e:
        flash(f'Report error: {e}', 'danger')
        return redirect(url_for('disease_prediction'))
@app.route('/api/community/posts')
def api_community_posts():
    posts = CommunityPost.query.order_by(CommunityPost.created_at.desc()).limit(20).all()
    return jsonify([{'id':p.id,'title':p.title,'body':p.body,'crop':p.crop,
        'district':p.district,'likes':p.likes,'farmer':p.farmer.name if p.farmer else 'Farmer',
        'time':p.created_at.strftime('%d %b'),'replies':CommunityReply.query.filter_by(post_id=p.id).count()} for p in posts])

@app.route('/api/community/post', methods=['POST'])
@login_required
def api_community_post():
    data = request.get_json() or {}
    post = CommunityPost(farmer_id=current_user.id,title=data.get('title',''),
        body=data.get('body',''),crop=data.get('crop',''),district=data.get('district',''))
    db.session.add(post); db.session.commit()
    return jsonify({'status':'ok','id':post.id})

@app.route('/api/community/reply', methods=['POST'])
@login_required
def api_community_reply():
    data = request.get_json() or {}
    db.session.add(CommunityReply(post_id=data.get('post_id'),farmer_id=current_user.id,body=data.get('body','')))
    db.session.commit()
    return jsonify({'status':'ok'})

@app.route('/api/community/like/<int:post_id>', methods=['POST'])
@login_required
def api_community_like(post_id):
    p = CommunityPost.query.get_or_404(post_id)
    p.likes = (p.likes or 0) + 1; db.session.commit()
    return jsonify({'likes':p.likes})

@app.route('/api/community/replies/<int:post_id>')
def api_community_replies(post_id):
    rs = CommunityReply.query.filter_by(post_id=post_id).order_by(CommunityReply.created_at).all()
    return jsonify([{'farmer':r.farmer.name if r.farmer else 'Farmer','body':r.body,'time':r.created_at.strftime('%d %b %H:%M')} for r in rs])

@app.route('/api/disease_alerts')
def api_disease_alerts():
    alerts = DiseaseAlert.query.order_by(DiseaseAlert.created_at.desc()).limit(10).all()
    result = [{'disease':a.disease,'crop':a.crop,'state':a.state,'district':a.district,
        'severity':a.severity,'count':a.report_count,'time':a.created_at.strftime('%d %b')} for a in alerts]
    if not result:
        recent = DiseaseDetection.query.order_by(DiseaseDetection.created_at.desc()).limit(8).all()
        seen = set()
        for d in recent:
            if d.disease_name not in seen:
                seen.add(d.disease_name)
                result.append({'disease':d.disease_name,'crop':'Multiple','state':'Telangana','district':'Hyderabad','severity':'Moderate','count':1,'time':d.created_at.strftime('%d %b')})
    if not result:
        result = [
            {'disease':'Bacterial Wilt','crop':'Tomato','state':'Telangana','district':'Warangal','severity':'Severe','count':14,'time':'Today'},
            {'disease':'Leaf Rust','crop':'Wheat','state':'AP','district':'Guntur','severity':'Moderate','count':8,'time':'Today'},
            {'disease':'Powdery Mildew','crop':'Cucumber','state':'Telangana','district':'Karimnagar','severity':'Mild','count':5,'time':'Yesterday'},
            {'disease':'Yellow Mosaic Virus','crop':'Soybean','state':'Maharashtra','district':'Nagpur','severity':'Severe','count':11,'time':'Yesterday'},
        ]
    return jsonify(result)

@app.route('/api/news_alerts')
def api_news_alerts():
    lang = session.get('language','en')
    news_db = NewsAlert.query.order_by(NewsAlert.created_at.desc()).limit(8).all()
    if news_db:
        return jsonify([{'title':n.title,'body':n.body,'category':n.category,'icon':n.icon,'time':n.created_at.strftime('%d %b')} for n in news_db])
    D = {
        'en':[
            {'icon':'🌧️','category':'Weather','title':'NE Monsoon Active — AP & Telangana','body':'Heavy rainfall next 5 days. Delay spray operations. Ensure field drainage.','time':'Today'},
            {'icon':'💰','category':'Market','title':'Tomato Prices Up 40% at Hyderabad','body':'Tomato wholesale now ₹28/kg. Good time to sell stored produce.','time':'Today'},
            {'icon':'🐛','category':'Alert','title':'Fall Armyworm Alert in Maize Fields','body':'FAW infestation in Warangal & Khammam. Apply Spinetoram 11.7% SC.','time':'Yesterday'},
            {'icon':'🏛️','category':'Scheme','title':'PM-KISAN 19th Installment Released','body':'₹2000 being credited to eligible farmers. Helpline: 155261.','time':'2 days ago'},
            {'icon':'🌱','category':'Advisory','title':'Rabi Soil Preparation Time','body':'Apply FYM 5 ton/acre before Rabi sowing. Add lime if pH below 6.0.','time':'3 days ago'},
        ],
        'te':[
            {'icon':'🌧️','category':'వాతావరణం','title':'AP & తెలంగాణలో ఈశాన్య రుతుపవనాలు','body':'వచ్చే 5 రోజులు భారీ వర్షాలు. స్ప్రే వాయిదా వేయండి.','time':'ఈరోజు'},
            {'icon':'💰','category':'మార్కెట్','title':'హైదరాబాద్‌లో టమాటా ధర 40% పెరిగింది','body':'మండీలో టమాటా ₹28/kg. నిల్వ పంటలు అమ్మండి.','time':'ఈరోజు'},
            {'icon':'🐛','category':'హెచ్చరిక','title':'మొక్కజొన్నలో ఆర్మీవార్మ్ హెచ్చరిక','body':'వరంగల్ & ఖమ్మంలో FAW సోకింది. Spinetoram వేయండి.','time':'నిన్న'},
            {'icon':'🏛️','category':'పథకం','title':'PM-KISAN 19వ విడత విడుదల','body':'₹2000 మీ ఖాతాకు జమ అవుతోంది. హెల్ప్‌లైన్: 155261.','time':'2 రోజుల క్రితం'},
            {'icon':'🌱','category':'సలహా','title':'రబీ సీజన్ మట్టి సన్నాహం','body':'రబీ విత్తనానికి ముందు 5 టన్/ఎకరా FYM వేయండి.','time':'3 రోజుల క్రితం'},
        ],
        'hi':[
            {'icon':'🌧️','category':'मौसम','title':'AP और तेलंगाना में मानसून सक्रिय','body':'अगले 5 दिन भारी बारिश। स्प्रे रोकें। जल निकासी सुनिश्चित करें।','time':'आज'},
            {'icon':'💰','category':'बाजार','title':'हैदराबाद में टमाटर 40% महंगा','body':'थोक ₹28/kg। संग्रहित उपज बेचने का अच्छा समय।','time':'आज'},
            {'icon':'🐛','category':'अलर्ट','title':'मक्का में फॉल आर्मीवर्म अलर्ट','body':'वारंगल और खम्मम में संक्रमण। Spinetoram 11.7% SC लगाएं।','time':'कल'},
            {'icon':'🏛️','category':'योजना','title':'PM-KISAN 19वीं किस्त जारी','body':'₹2000 मिल रहे हैं। हेल्पलाइन: 155261.','time':'2 दिन पहले'},
            {'icon':'🌱','category':'सलाह','title':'रबी सीजन की तैयारी','body':'बुवाई से पहले 5 टन/एकड़ FYM डालें।','time':'3 दिन पहले'},
        ]
    }
    return jsonify(D.get(lang,D['en']))

@app.route('/api/bookmark_disease', methods=['POST'])
@login_required
def api_bookmark_disease():
    data = request.get_json() or {}
    det_id = data.get('detection_id')
    ex = BookmarkedDisease.query.filter_by(farmer_id=current_user.id,detection_id=det_id).first()
    if ex:
        db.session.delete(ex); db.session.commit(); return jsonify({'status':'removed'})
    db.session.add(BookmarkedDisease(farmer_id=current_user.id,detection_id=det_id))
    db.session.commit(); return jsonify({'status':'added'})

@app.route('/api/bookmarks')
@login_required
def api_bookmarks():
    bms = BookmarkedDisease.query.filter_by(farmer_id=current_user.id).all()
    result = []
    for b in bms:
        d = DiseaseDetection.query.get(b.detection_id)
        if d: result.append({'id':d.id,'disease':d.disease_name,'confidence':d.confidence,'image':d.image_path,'time':d.created_at.strftime('%d %b %Y')})
    return jsonify(result)

@app.route('/nearest-mandi')
@login_required
def nearest_mandi():
    state    = current_user.state    or 'Telangana'
    district = current_user.district or 'Warangal'
    return render_template('nearest_mandi.html',
                           state=state,
                           district=district,
                           districts=STATES_DISTRICTS,
                           states=list(STATES_DISTRICTS.keys()))

@app.route('/api/nearest-mandi/<crop>/<state>/<district>')
@login_required
def api_nearest_mandi(crop, state, district):
    import requests as req, math

    CROP_MAP = {
        'Tomato':'Tomato','Onion':'Onion','Potato':'Potato',
        'Chilli':'Chilli(Dry)','Maize':'Maize',
        'Paddy':'Paddy(Common)','Cotton':'Cotton',
        'Soybean':'Soyabean','Groundnut':'Groundnut',
        'Wheat':'Wheat','Rice':'Rice','Turmeric':'Turmeric',
        'Redgram':'Arhar (Tur/Red Gram)(Whole)',
        'Chickpea':'Bengal Gram(Gram)(Whole)',
        'Sunflower':'Sunflower','Mustard':'Mustard',
        'Moong':'Moong (Whole)','Garlic':'Garlic',
        'Banana':'Banana','Mango':'Mango',
        'Jowar':'Jowar(Sorghum)','Bajra':'Bajra(Pearl Millet/Cumbu)',
        'Ragi':'Ragi (Finger Millet)','Castor':'Castor Seed',
        'Sesame':'Sesamum(Sesame/Til)','Cumin':'Cummin Seed(Jeera)',
        'Coriander':'Coriander(Leaves)','Ginger':'Ginger(Dry)',
        'Horsegram':'Horse Gram','Coconut':'Coconut',
        'Grapes':'Grapes','Watermelon':'Water Melon',
        'Brinjal':'Brinjal','Sugarcane':'Sugarcane',
        'Tobacco':'Tobacco','Tur':'Arhar (Tur/Red Gram)(Whole)',
    }

    # All district coordinates — used to calculate real distance
    ALL_COORDS = {
        # TELANGANA
        'Karimnagar':(18.4386,79.1288),'Warangal':(17.9784,79.5941),
        'Hanamkonda':(18.0,79.58),'Khammam':(17.2473,80.1514),
        'Nalgonda':(17.05,79.266),'Mahabubnagar':(16.7374,77.987),
        'Nizamabad':(18.6725,78.0941),'Adilabad':(19.664,78.532),
        'Mancherial':(18.87,79.46),'Hyderabad':(17.385,78.4867),
        'Medak':(18.044,78.263),'Sangareddy':(17.624,78.087),
        'Siddipet':(18.102,78.852),'Suryapet':(17.141,79.622),
        'Jagtial':(18.794,78.914),'Kamareddy':(18.322,78.34),
        'Peddapalli':(18.615,79.383),'Nirmal':(19.094,78.344),
        'Mulugu':(18.196,80.054),'Nagarkurnool':(16.48,78.324),
        'Wanaparthy':(16.362,78.064),'Vikarabad':(17.337,77.905),
        'Yadadri Bhuvanagiri':(17.56,78.992),
        'Rajanna Sircilla':(18.387,78.812),
        'Jogulamba Gadwal':(16.234,77.803),
        'Bhadradri Kothagudem':(17.556,80.619),
        'Jayashankar Bhupalpally':(18.442,79.891),
        'Komaram Bheem Asifabad':(19.366,79.28),
        'Mahabubabad':(17.599,80.002),
        'Jangaon':(17.724,79.152),
        'Rangareddy':(17.3616,78.3837),
        'Medchal-Malkajgiri':(17.554,78.532),
        'Narayanpet':(16.744,77.494),
        # ANDHRA PRADESH
        'Guntur':(16.3067,80.4365),'Kurnool':(15.8281,78.0373),
        'Vijayawada':(16.5062,80.648),'Visakhapatnam':(17.6868,83.2185),
        'Nellore':(14.4426,79.9865),'Anantapur':(14.6819,77.6006),
        'Kadapa':(14.4674,78.8241),'Tirupati':(13.6288,79.4192),
        'Eluru':(16.7107,81.0952),'Ongole':(15.5057,80.0499),
        # MAHARASHTRA
        'Nagpur':(21.1458,79.0882),'Nashik':(19.9975,73.7898),
        'Pune':(18.5204,73.8567),'Aurangabad':(19.8762,75.3433),
        'Amravati':(20.9374,77.7796),'Latur':(18.4088,76.5604),
        'Solapur':(17.6805,75.9064),'Kolhapur':(16.705,74.2433),
        # KARNATAKA
        'Hubli':(15.3647,75.124),'Bengaluru':(12.9716,77.5946),
        'Mysuru':(12.2958,76.6394),'Belagavi':(15.8497,74.4977),
        'Dharwad':(15.4589,75.0078),'Davanagere':(14.4644,75.9218),
        # MADHYA PRADESH
        'Bhopal':(23.2599,77.4126),'Indore':(22.7196,75.8577),
        'Nagpur':(21.1458,79.0882),'Khargone':(21.8234,75.613),
        'Jhabua':(22.7676,74.589),'Burhanpur':(21.3086,76.2294),
        # OTHERS
        'Jaipur':(26.9124,75.7873),'Jodhpur':(26.2389,73.0243),
        'Lucknow':(26.8467,80.9462),'Ahmedabad':(23.0225,72.5714),
        'Chennai':(13.0827,80.2707),'Durg':(21.1904,81.2849),
        'Hissar':(29.1492,75.7217),'Sabarkantha':(23.588,72.972),
        'Dharmapuri':(12.1278,78.158),'Karur':(10.9601,78.0766),
        'Sambhal':(28.5906,78.5692),'Ludhiana':(30.901,75.8573),
    }

    MANDI_TYPES = ['APMC','Wholesale','Rythu Bazar','Private Market','Cooperative']

    NEARBY_STATES = {
        'Telangana':['Andhra Pradesh','Maharashtra','Karnataka'],
        'Andhra Pradesh':['Telangana','Karnataka','Tamil Nadu'],
        'Maharashtra':['Telangana','Karnataka','Madhya Pradesh'],
        'Karnataka':['Andhra Pradesh','Telangana','Tamil Nadu'],
        'Tamil Nadu':['Andhra Pradesh','Karnataka'],
        'Uttar Pradesh':['Madhya Pradesh','Rajasthan','Bihar'],
        'Punjab':['Haryana','Rajasthan'],
        'Rajasthan':['Gujarat','Madhya Pradesh','Uttar Pradesh'],
        'Madhya Pradesh':['Maharashtra','Rajasthan','Uttar Pradesh'],
        'Gujarat':['Rajasthan','Madhya Pradesh','Maharashtra'],
    }

    # Haversine distance in km (server-side)
    def haversine(lat1, lon1, lat2, lon2):
        R = 6371
        dL = math.radians(lat2 - lat1)
        dl = math.radians(lon2 - lon1)
        a  = math.sin(dL/2)**2 + math.cos(math.radians(lat1)) * \
             math.cos(math.radians(lat2)) * math.sin(dl/2)**2
        return round(R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a)), 1)

    agmark_name = CROP_MAP.get(crop)
    if not agmark_name:
        return jsonify({'crop':crop,'state':state,
                        'district':district,'mandis':[],'count':0})

    # Get farmer district coordinates
    farmer_coords = ALL_COORDS.get(district)

    records = []

    # ── Fetch same state ──────────────────────────────────────────
    try:
        url = (
            "https://api.data.gov.in/resource/"
            "9ef84268-d588-465a-a308-a864a43d0070"
            f"?api-key={DATAGOV_KEY}&format=json&limit=50"
            f"&filters[commodity]={agmark_name}"
            f"&filters[state.keyword]={state}"
        )
        resp    = req.get(url, timeout=3
                          )
        records = resp.json().get('records', [])
        print(f"✅ {state} records: {len(records)}")
    except Exception as e:
        print(f"⚠️ State fetch error: {e}")

    # ── If less than 5, add nearby states ────────────────────────
    if len(records) < 5:
        for ns in NEARBY_STATES.get(state, [])[:2]:
            try:
                url2 = (
                    "https://api.data.gov.in/resource/"
                    "9ef84268-d588-465a-a308-a864a43d0070"
                    f"?api-key={DATAGOV_KEY}&format=json&limit=20"
                    f"&filters[commodity]={agmark_name}"
                    f"&filters[state.keyword]={ns}"
                )
                r2 = req.get(url2, timeout=3).json().get('records', [])
                records += r2
                print(f"➕ {ns}: {len(r2)} records")
            except:
                pass

    # ── Still empty — all India fallback ─────────────────────────
    if not records:
        try:
            url3 = (
                "https://api.data.gov.in/resource/"
                "9ef84268-d588-465a-a308-a864a43d0070"
                f"?api-key={DATAGOV_KEY}&format=json&limit=30"
                f"&filters[commodity]={agmark_name}"
            )
            records = req.get(url3, timeout=3).json().get('records', [])
            print(f"🌍 All India fallback: {len(records)}")
        except:
            pass

    # ── Build mandi list with REAL distances ──────────────────────
    seen   = set()
    mandis = []

    for i, r in enumerate(records):
        try:
            modal = float(r.get('modal_price', 0))
            min_p = float(r.get('min_price',   0))
            max_p = float(r.get('max_price',   0))
            if modal <= 0:
                continue
            mkt = r.get('market', 'Unknown')
            if mkt in seen:
                continue
            seen.add(mkt)

            rec_district = r.get('district', '')
            rec_state    = r.get('state', state)
            coords       = ALL_COORDS.get(rec_district)

            # Calculate server-side distance from farmer's district
            if farmer_coords and coords:
                dist_km = haversine(
                    farmer_coords[0], farmer_coords[1],
                    coords[0], coords[1]
                )
            else:
                # Estimate: same state = closer, other state = farther
                dist_km = 50 if rec_state == state else 300

            mandis.append({
                'mandi'      : mkt,
                'district'   : rec_district,
                'state'      : rec_state,
                'min'        : round(min_p  / 100, 2),
                'modal'      : round(modal  / 100, 2),
                'max'        : round(max_p  / 100, 2),
                'date'       : r.get('arrival_date', 'Today'),
                'lat'        : coords[0] if coords else None,
                'lng'        : coords[1] if coords else None,
                'distance_km': dist_km,
                'type'       : MANDI_TYPES[i % len(MANDI_TYPES)],
                'maps_url'   : (
                    f"https://www.google.com/maps/dir/?api=1"
                    f"&destination={coords[0]},{coords[1]}"
                    if coords else
                    f"https://www.google.com/maps/search/"
                    f"{mkt.replace(' ','+')}+{rec_district}"
                ),
            })
        except:
            continue

    # ── Sort by distance — nearest first ─────────────────────────
    mandis.sort(key=lambda x: x['distance_km'])

    print(f"✅ Final: {len(mandis)} mandis sorted by distance from {district}")

    return jsonify({
        'crop'    : crop,
        'state'   : state,
        'district': district,
        'mandis'  : mandis[:12],
        'count'   : len(mandis),
    })
@app.route('/cultivation')
@login_required
def cultivation():
    return render_template('cultivation.html')


from gtts import gTTS

@app.route('/api/tts')
def tts():
    text = request.args.get('text', '')
    lang = request.args.get('lang', 'en')
    if not text:
        return '', 400
    lang_map = {'en': 'en', 'hi': 'hi', 'te': 'te'}
    lang_code = lang_map.get(lang, 'en')
    try:
        tts_obj = gTTS(text=text[:500], lang=lang_code, slow=False)
        buf = io.BytesIO()
        tts_obj.write_to_fp(buf)
        buf.seek(0)
        return send_file(buf, mimetype='audio/mpeg')
    except Exception as e:
        return str(e), 500
        
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
    
    