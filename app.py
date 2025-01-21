from flask import Flask,request,redirect,render_template,url_for,flash,session
from otp import genotp
from stoken import encode,decode
from cmail import sendmail
import os
import re
#import razorpay
import mysql.connector
#mytdb=mysql.connector.connect(host='localhost',user='root',password='admin',db='ecommi')
user=os.environ.get('RDS_USERNAME')
db=os.environ.get('RDS_DB_NAME')
password=os.environ.get('RDS_PASSWORD')
host=os.environ.get('RDS_HOSTNAME')
port=os.environ.get('RDS_PORT')
with mysql.connector.connect(host=host,port=port,db=db,password=password,user=user) as conn:
    cursor=conn.cursor()
    cursor.execute("CREATE TABLE if not exists usercreate (username varchar(50) NOT NULL,user_email varchar(100) NOT NULL,address text NOT NULL,password varbinary(20) NOT NULL,gender enum('Male','Female') DEFAULT NULL,PRIMARY KEY (user_email),UNIQUE KEY username (username))")
    cursor.execute("CREATE TABLE if not exists admincreate (email varchar(50) NOT NULL,username varchar(100) NOT NULL,password varbinary(10) NOT NULL,address text NOT NULL,accept enum('on','off') DEFAULT NULL,dp_image varchar(50) DEFAULT NULL,ph_no bigint DEFAULT NULL,PRIMARY KEY (email),UNIQUE KEY ph_no (ph_no))")
    cursor.execute("CREATE TABLE if not exists contactus (name varchar(100) DEFAULT NULL,email varchar(100) DEFAULT NULL,message text)")
    cursor.execute("CREATE TABLE if not exists orders (orderid bigint NOT NULL AUTO_INCREMENT,itemid binary(16) DEFAULT NULL,item_name longtext,qty int DEFAULT NULL,total_price bigint DEFAULT NULL,user varchar(100) DEFAULT NULL,PRIMARY KEY (orderid),KEY user (user),KEY itemid (itemid),CONSTRAINT orders_ibfk_1 FOREIGN KEY (user) REFERENCES usercreate (user_email),CONSTRAINT orders_ibfk_2 FOREIGN KEY (itemid) REFERENCES items (item_id))")
    cursor.execute("CREATE TABLE if not exists reviews (username varchar(30) NOT NULL,itemid binary(16) NOT NULL,title tinytext,review text,rating int DEFAULT NULL,date datetime DEFAULT CURRENT_TIMESTAMP,PRIMARY KEY (itemid,username),KEY username (username),CONSTRAINT reviews_ibfk_1 FOREIGN KEY (itemid) REFERENCES items (item_id) ON DELETE CASCADE ON UPDATE CASCADE,CONSTRAINT reviews_ibfk_2 FOREIGN KEY (username) REFERENCES usercreate (user_email) ON DELETE CASCADE ON UPDATE CASCADE)")
    cursor.execute("CREATE TABLE if not exists items (item_id binary(16) NOT NULL,item_name varchar(255) NOT NULL,quantity int unsigned DEFAULT NULL,price decimal(14,4) NOT NULL,category enum('Home_appliances','Electronics','Fashion','Grocery') DEFAULT NULL,image_name varchar(255) NOT NULL,added_by varchar(50) DEFAULT NULL,description longtext,PRIMARY KEY (item_id),KEY added_by (added_by),CONSTRAINT items_ibfk_1 FOREIGN KEY (added_by) REFERENCES admincreate (email) ON DELETE CASCADE ON UPDATE CASCADE)")
mytdb=mysql.connector.connect(host=host,user=user,port=port,db=db,password=password)
app=Flask(__name__)
app.config['SESSION_TYPE']='filesystem'
app.secret_key='code@123'
RAZORPAY_KEY_ID='rzp_test_BdYxoi5GaEITjc'
RAZORPAY_KEY_SECRET='H0FUH2n4747ZSYBRyCn2D6rc'

#client=razorpay.Client(auth=(RAZORPAY_KEY_ID,RAZORPAY_KEY_SECRET))
@app.route('/')
def home():
    return render_template('welcome.html')
@app.route('/index')
def index():
    try:
        cursor=mytdb.cursor(buffered=True)
        cursor.execute('select bin_to_uuid(item_id),item_name,quantity,price,category,image_name from items')
        items_data=cursor.fetchall() #retriving all the items from items table
    except Exception as e:
        print(e)
        flash("could'n fetch items")  
        return redirect(url_for('home'))
    else:
        return render_template('index.html',items_data=items_data)    
@app.route('/admincreate',methods=['GET','POST'])
def admincreate():
    if request.method=='POST':
        print(request.form)
        aname=request.form['username'] #yashu
        aemail=request.form['email'] #yasaswini099@gmail.com
        password=request.form['password'] #123
        address=request.form['address'] #my address
        status_accept=request.form['agree'] #agree to terms
        cursor=mytdb.cursor(buffered= True)
        cursor.execute('select count(email) from admincreate where email=%s',[aemail])
        email_count=cursor.fetchone()
        if email_count[0]==0:
            otp=genotp()
            admindata={'aname':aname,'aemail':aemail,'password':password,'address':address,'accept':status_accept,'aotp':otp}
            subject='Ecommerce verfication mail'
            body=f'Ecommerce verification otp for admin registration {otp}'
            sendmail(to=aemail,subject=subject,body=body)
            flash('OTP has sent to given mail')
            return redirect(url_for('otp',paotp=encode(data=admindata))) #encode otp
        elif email_count[0]==1:
            flash('email already register pls check')
            return redirect(url_for('adminlogin'))
    return render_template('admincreate.html')
@app.route('/otp <paotp>',methods=['GET','POST'])
def otp(paotp):
    if request.method=='POST':
        fotp=request.form['otp'] #user given otp
        try:
            d_data=decode(data=paotp) #decoding the tokenised data {'aname':aname,'aemail':aemail,'password':password,'address':address,'accept':status_accept,'aotp':otp}
        except Exception as e:
            print (e)
            flash('something went wrong')
            return redirect(url_for('admincreate'))
        else:    
            if d_data['aotp']==fotp: #comparing the fotp with generated otp
                cursor=mytdb.cursor(buffered=True)
                cursor.execute('insert into admincreate(email,username,password,address,accept) values(%s,%s,%s,%s,%s)',[d_data['aemail'],d_data['aname'],d_data['password'],d_data['address'],d_data['accept']])
                mytdb.commit()
                cursor.close()
                flash('Registeration successful')
                return redirect(url_for('adminlogin'))
            else:
                flash('wrong otp,please enter correct otp')
                return redirect(url_for('admincreate'))
    return render_template('adminotp.html')
@app.route('/adminlogin',methods=['GET','POST'])
def adminlogin():
    if not session.get('admin'):
        if request.method=='POST':
            login_email=request.form['email']
            login_password=request.form['password']
            try:
                cursor=mytdb.cursor(buffered=True)
                cursor.execute('select count(email) from admincreate where email=%s',[login_email])
                stored_emailcount=cursor.fetchone()
            except Exception as e:
                print(e)
                flash('Connection Error')
                return redirect(url_for('adminlogin'))
            else:
                if stored_emailcount[0]==1:
                    cursor.execute('select password from admincreate where email=%s',[login_email])
                    stored_password=cursor.fetchone()
                    if login_password==stored_password[0].decode('utf-8'):
                        print(session)
                        session['admin']=login_email
                        if not session.get(login_email):
                            session[login_email]={}
                            print(session)
                        return redirect(url_for('adminpanel'))
                    else:
                        flash('password was wrong')
                        return redirect(url_for ('adminlogin'))
                else:
                    flash('Email was wrong')
                    return redirect(url_for('adminlogin'))
        return render_template('adminlogin.html')
    else:
        return redirect(url_for('adminpanel'))
@app.route('/adminpanel')
def adminpanel():
    if session.get('admin'):
        return render_template('adminpanel.html')
    else:
        return redirect(url_for('adminlogin'))
@app.route('/adminforgot',methods=['GET','POST'])
def adminforgot():
    if request.method=='POST':
        forgot_email=request.form['email'] #accepting user email
        cursor=mytdb.cursor(buffered=True)
        cursor.execute('select count(email) from admincreate where email=%s',[forgot_email])
        stored_email=cursor.fetchone()
        if stored_email[0]==1:
            subject='Admin Reset link for ecommy application'
            body=f"Click on the link for update password:{url_for('ad_password_update',token=encode(data=forgot_email),_external=True)}"
            sendmail(to=forgot_email,subject=subject,body=body)
            flash(f'Reset link has send to give {forgot_email}')
            return redirect(url_for('adminforgot'))
        elif stored_email[0]==0:
            flash('No email registered please check')
            return redirect(url_for('adminlogin'))
    return render_template('forgot.html')    
@app.route('/ad_password_update/<token>',methods=['GET','POST'])
def ad_password_update(token): 
    if request.method=='POST':
        try:
            npassword=request.form['npassword']
            cpassword=request.form['cpassword']
            dtoken=decode(data=token)
        except Exception as e:
            print(e)
            flash('something went wrong')
        else:
            if npassword==cpassword:
                cursor=mytdb.cursor(buffered=True)
                cursor.execute('update admincreate set password=%s where email=%s',[npassword,dtoken])
                mytdb.commit()
                flash('password updated successfully')
                return redirect(url_for('adminlogin'))
            else:
                flash('password mismatched')
                return redirect(url_for('ad_password_update',token=token))        
    return render_template('newpassword.html') 
@app.route('/logout')
def logout():
    if session.get('admin'):
        session.pop('admin')
        return redirect(url_for('home'))
    else:
        return redirect(url_for('adminlogin')) 
@app.route('/additem',methods=['GET','POST'])   
def additem():
    if session.get('admin'):
        if request.method=='POST':
            title=request.form['title']
            description=request.form['Discription']
            price=request.form['price']
            category=request.form['category']
            quantity=request.form['quantity']
            img_file=request.files['file']
            print(img_file.filename.split('.'))
            img_name=genotp()+'.'+img_file.filename.split('.')[-1] #creating a filename using user extention
            '''to store the img in static folder,we need to get the path without system varies'''
            drname=os.path.dirname(os.path.abspath(__file__)) #C:\Users\91630\Desktop\framework\ECOM
            static_path=os.path.join(drname,'static') #C:\Users\91630\Desktop\framework\ECOM\static
            img_file.save(os.path.join(static_path,img_name))
            try:
                cursor=mytdb.cursor(buffered=True)
                cursor.execute('insert into items(item_id,item_name,description,price,quantity,category,image_name,added_by) values(uuid_to_bin(uuid()),%s,%s,%s,%s,%s,%s,%s)',[title,description,price,quantity,category,img_name,session.get('admin')])
                mytdb.commit()
                cursor.close()
            except Exception as e:
                print(e)
                flash('Connection Error')
                return redirect(url_for('additem'))
            else:
                flash(f'{title[:10]}.. added successfully')
                return redirect(url_for('additem'))    
        return render_template('additem.html')
    else:
        return redirect(url_for('adminlogin'))  
@app.route('/viewallitems')
def viewallitems():
    if session.get('admin'):
        try:
            cursor=mytdb.cursor(buffered=True)
            cursor.execute('select bin_to_uuid(item_id),item_name,image_name from items where added_by=%s',[session.get('admin')])
            stored_items=cursor.fetchall()
        except Exception as e:
            print(e)
            flash('connection problem')
            return redirect(url_for('adminpanel'))
        else:
            return render_template('viewall_items.html',stored_items=stored_items)
    else:
        return redirect(url_for('adminlogin'))  
@app.route('/deleteitem/<item_id>')
def deleteitem(item_id):
    try:
        cursor=mytdb.cursor(buffered=True)
        cursor.execute('select image_name from items where item_id=uuid_to_bin(%s)',[item_id])
        stored_image=cursor.fetchone()
        drname=os.path.dirname(os.path.abspath(__file__)) #C:\Users\91630\Desktop\framework\ECOM
        static_path=os.path.join(drname,'static') #C:\Users\91630\Desktop\framework\ECOM\static    
        if stored_image in os.listdir(static_path):
            os.remove(os.path.join(static_path,stored_image[0]))
        cursor.execute('delete from items where item_id=uuid_to_bin(%s)',[item_id])
        mytdb.commit() 
        cursor.close()     
    except Exception as e:
        print(e)
        flash("couldn't delete item")
        return redirect(url_for('viewallitems'))
    else:
        flash("item deleted successfully")
        return redirect(url_for('viewallitems')) 
@app.route('/viewitem/<item_id>')
def viewitem(item_id):
    if session.get('admin'):
        try:
            cursor=mytdb.cursor(buffered=True)
            cursor.execute('select bin_to_uuid(item_id),item_name,description,price,quantity,category,image_name from items where item_id=uuid_to_bin(%s)',[item_id])
            item_data=cursor.fetchone()
        except Exception as e:
            print(e)
            flash('connection error')
            return redirect(url_for('viewallitems'))    
        else:
            return render_template('view_item.html',item_data=item_data)
    else:
        return redirect(url_for('adminlogin'))    
@app.route('/updateitem/<item_id>',methods=['GET','POST'])
def updateitem(item_id):
    if session.get('admin'):
        try:
            cursor=mytdb.cursor(buffered=True)
            cursor.execute('select bin_to_uuid(item_id),item_name,description,price,quantity,category,image_name from items where item_id=uuid_to_bin(%s)',[item_id])
            item_data=cursor.fetchone() #(item_id,item_name)
        except Exception as e:
            print(e)
            flash('connection error')
            return redirect(url_for('viewallitems'))
        else:
            if request.method=='POST':
                title=request.form['title']
                description=request.form['Discription']
                price=request.form['price']
                category=request.form['category']
                quantity=request.form['quantity']
                img_file=request.files['file']
                filename=img_file.filename #fetch the filename
                print(img_file,11) #to check how image is displaying on frontend page
                if filename =='':
                    img_name=item_data[6] #updating with old name
                else:
                    img_name=genotp()+'.'+filename.split('.')[-1] #creating new filename if new image is uploaded
                    drname=os.path.dirname(os.path.abspath(__file__)) #C:\Users\91630\Desktop\framework\ECOM
                    static_path=os.path.join(drname,'static') #C:\Users\91630\Desktop\framework\ECOM\static
                    if item_data[6] in os.listdir(static_path):
                        os.remove(os.path.join(static_path,item_data[6]))
                    img_file.save(os.path.join(static_path,img_name))
                cursor=mytdb.cursor(buffered=True)
                cursor.execute('update items set item_name=%s,description=%s,price=%s,quantity=%s,category=%s,image_name=%s where item_id=uuid_to_bin(%s)',[title,description,price,quantity,category,img_name,item_id]) 
                mytdb.commit()
                cursor.close()
                flash('items updated successfully')
                return redirect(url_for('viewitem',item_id=item_id))
            return render_template('update_item.html',data=item_data)
    else:
        return redirect(url_for('adminlogin'))
@app.route('/adminprofileupdate',methods=['GET','POST'])
def adminprofileupdate():
    if session.get('admin'):
        try:
            cursor=mytdb.cursor(buffered=True)
            cursor.execute('select username,address,dp_image from admincreate where email=%s',[session.get('admin')])
            admin_data=cursor.fetchone()
        except Exception as e:
            print(e)
            flash('connection error')
            return redirect(url_for('adminpanel'))    
        else:
             if request.method == 'POST':
                username = request.form['adminname']
                address = request.form['address']
                img_data = request.files['file']
                filename = img_data.filename
                print(filename,22)
                if filename == '':
                    img_name = admin_data[2]
                else:
                    img_name = genotp() + '.' + filename.split('.')[-1] #createing new filename
                    drname = os.path.dirname(os.path.abspath(__file__))
                    static_path = os.path.join(drname,'static')
                    if admin_data[2] in os.listdir(static_path):  #if old image exist in static folder
                        os.remove(os.path.join(static_path,admin_data[2]))
                    img_data.save(os.path.join(static_path,img_name)) #saving new file in static
                cursor.execute('update admincreate set username=%s, address=%s, dp_image=%s where email=%s',[username,address,img_name,session.get('admin')])
                mytdb.commit()
                cursor.close()
                flash('Profile update succesfully')
                return redirect(url_for('adminprofileupdate'))
             return render_template('adminupdate.html',admin_data=admin_data)
    else:    
        return render_template('adminlogin.html') 
@app.route('/usersignup',methods=['GET','POST'])
def usersignup():
    if request.method=='POST':
        print(request.form)
        uname=request.form['username'] #yashu
        uemail=request.form['email'] #yasaswini099@gmail.com
        address=request.form['address'] #my address
        password=request.form['password'] #123
        #status_accept=request.form['agree'] #agree to terms
        cursor=mytdb.cursor(buffered= True)
        cursor.execute('select count(user_email) from usercreate where user_email=%s',[uemail])
        email_count=cursor.fetchone()
        if email_count[0]==0:
            otp=genotp()
            userdata={'uname':uname,'uemail':uemail,'password':password,'address':address,'uotp':otp}
            subject='Ecommerce verfication mail'
            body=f'Ecommerce verification otp for admin registration {otp}'
            sendmail(to=uemail,subject=subject,body=body)
            flash('OTP has sent to given mail')
            return redirect(url_for('ootp',passotp=encode(data=userdata))) #encode otp
        elif email_count[0]==1:
            flash('email already register pls check')
            return redirect(url_for('userlogin'))
    return render_template('usersignup.html')
@app.route('/ootp <passotp>',methods=['GET','POST'])
def ootp(passotp):
    if request.method=='POST':
        hotp=request.form['otp'] #user given otp
        try:
            de_data=decode(data=passotp) #decoding the tokenised data {'uname':uname,'uemail':uemail,'password':password,'address':address,'accept':status_accept,'uotp':otp}
        except Exception as e:
            print (e)
            flash('something went wrong')
            return redirect(url_for('usersignup'))
        else:    
            if de_data['uotp']==hotp: #comparing the ootp with generated otp
                cursor=mytdb.cursor(buffered=True)
                cursor.execute('insert into usercreate(username,user_email,password,address) values(%s,%s,%s,%s)',[de_data['uname'],de_data['uemail'],de_data['password'],de_data['address']])
                mytdb.commit()
                cursor.close()
                flash('Registeration successful')
                return redirect(url_for('userlogin'))
            else:
                flash('wrong otp,please enter correct otp')
                return redirect(url_for('usersignup'))
    return render_template('userotp.html')
@app.route('/userlogin',methods=['GET','POST'])
def userlogin():
    if not session.get('user'):
        if request.method=='POST':
            #login_username=request.form['username']
            login_email=request.form['email']
            login_password=request.form['password']
            try:
                cursor=mytdb.cursor(buffered=True)
                cursor.execute('select count(user_email) from usercreate where user_email=%s',[login_email])
                stored_emailcount=cursor.fetchone()
            except Exception as e:
                print(e)
                flash('Connection Error')
                return redirect(url_for('userlogin'))
            else:
                if stored_emailcount[0]==1:
                    cursor.execute('select password from usercreate where user_email=%s',[login_email])
                    stored_password=cursor.fetchone()
                    if login_password==stored_password[0].decode('utf-8'):
                        print(session)
                        session['user']=login_email
                        if not session.get(login_email):
                            session[login_email]={}
                            print(session)
                        return redirect(url_for('index'))
                    else:
                        flash('password was wrong')
                        return redirect(url_for ('userlogin'))
                else:
                    flash('Email was wrong')
                    return redirect(url_for('userlogin'))
        return render_template('userlogin.html')
    else:
        return redirect(url_for('index')) 
#@app.route('/dashboard')
#def dashboard():
 #   if session.get('user'):
  #      return render_template('dashboard.html')
   # else:
    #    return redirect(url_for('userlogin'))
@app.route('/userforgot',methods=['GET','POST'])
def userforgot():
    if request.method=='POST':
        forgot_email=request.form['email'] #accepting user email
        cursor=mytdb.cursor(buffered=True)
        cursor.execute('select count(user_email) from usercreate where user_email=%s',[forgot_email])
        stored_email=cursor.fetchone()
        if stored_email[0]==1:
            subject='Admin Reset link for ecommy application'
            body=f"Click on the link for update password:{url_for('user_password_update',token=encode(data=forgot_email),_external=True)}"
            sendmail(to=forgot_email,subject=subject,body=body)
            flash(f'Reset link has send to give {forgot_email}')
            return redirect(url_for('userforgot'))
        elif stored_email[0]==0:
            flash('No email registered please check')
            return redirect(url_for('userlogin'))
    return render_template('forgot.html')    
@app.route('/user_password_update/<token>',methods=['GET','POST'])
def user_password_update(token): 
    if request.method=='POST':
        try:
            npassword=request.form['npassword']
            cpassword=request.form['cpassword']
            dtoken=decode(data=token)
        except Exception as e:
            print(e)
            flash('something went wrong')
        else:
            if npassword==cpassword:
                cursor=mytdb.cursor(buffered=True)
                cursor.execute('update usercreate set password=%s where user_email=%s',[npassword,dtoken])
                mytdb.commit()
                flash('password updated successfully')
                return redirect(url_for('userlogin'))
            else:
                flash('password mismatched')
                return redirect(url_for('user_password_update',token=token))        
    return render_template('newpassword.html')
@app.route('/userlogout')
def userlogout():
    if session.get('user'):
        session.pop('user')
        return redirect(url_for('index'))
    else:
        return redirect(url_for('userlogin'))
@app.route('/category/<type>')
def category(type):
    try:
        cursor=mytdb.cursor(buffered=True)
        cursor.execute('select bin_to_uuid(item_id),item_name,quantity,price,category,image_name from items')
        items_data=cursor.fetchall()
    except Exception as e:
        print(e)
        flash('could nit fetch items')
        return redirect(url_for('home'))
    return render_template('dashboard.html',items_data=items_data)
@app.route('/adminlogout')
def adminlogout():
    if session.get('admin'):
        session.pop('admin')
        return redirect(url_for('home'))
    else:
        return redirect(url_for('adminlogin')) 
@app.route('/addcart/<itemid>/<name>/<float:price>/<qyt>/<image>/<category>')  
def addcart(itemid,name,price,qyt,image,category):
    if not session.get('user'):
        return redirect(url_for(userlogin))
    else:
        print(session)
        if itemid not in session['user']:
            session[session.get('user')][itemid]=[name,price,1,image,category,qyt] 
            session.modified=True
            print(session)
            flash(f'{name} added to cart')
            return redirect(url_for('index'))
        session[session.get('user')][itemid][2]+=1
        flash('item already in cart')
        return redirect(url_for('index')) 
@app.route('/viewcart')
def viewcart():
    if not session.get('user'):
        return redirect(url_for('userlogin'))
    else:
        if session.get(session.get('user')):
            items=session[session.get('user')]
        else:
            items='empty'
        if items=='empty':
            flash('No products added to cart')
            return redirect(url_for('index'))
        return render_template('cart.html',items=items)        
@app.route('/removecart_item/<itemid>')
def removecart_item(itemid):
    if not session.get('user'):
        return redirect(url_for('userlogin'))
    else:
        session.get(session.get('user')).pop(itemid)
        session.modified=True
        flash('item removed from cart')
        return redirect(url_for('viewcart'))
@app.route('/description/<itemid>')
def description(itemid):
    try:
        cursor=mytdb.cursor(buffered=True)
        cursor.execute('select bin_to_uuid(item_id),item_name,description,quantity,price,category,image_name from items where item_id=uuid_to_bin(%s)',[itemid])
        item_data=cursor.fetchone() #retriving the item from items table
    except Exception as e:
        print(e)
        flash('could not fetch items')
        return redirect(url_for('index'))
    return render_template('description.html',item_data=item_data)
'''@app.route('/pay/<itemid>/<name>/<float:price>',methods=['GET','POST'])
def pay(itemid,name,price):
    try:
        qyt=int(request.form['qyt'])
        amount=price*100 #convert price into paise
        total_price=qyt*amount
        print(amount,qyt,total_price)
        print(f'Creating payment for item:{itemid},name:{name},price:{total_price}')
        #create Razorpay order
        order=client.order.create({
            'amount':total_price,
            'currency':'INR',
            'payment_capture':'1'
        })
        print(f"order created:{order}")
        return render_template('pay.html',order=order,itemid=itemid,name=name,price=price,qyt=qyt)
    except Exception as e:
        #log the error and return a 400 response
        print(f'Error creating order: {str(e)}')
        flash('Error in payment')
        return redirect(url_for('index'))
@app.route('/success',methods=['POST'])
def success():
    #extract payment details from the form
    payment_id=request.form.get('razorpay_payment_id')
    order_id=request.form.get('razorpay_order_id')
    signature_id=request.form.get('razorpay_signature')
    name=request.form.get('name')
    itemid=request.form.get('itemid')
    price=request.form.get('price')
    qyt=request.form.get('qyt')
    #verification process
    params_dict={
        'razorpay_payment_id':order_id,
        'razorpay_order_id':payment_id,
        'razorpay_signature':signature_id
    }
    try:
        client.utility.verify_payment_signature(params_dict)
        cursor=mytdb.cursor(buffered=True)
        cursor.execute('insert into orders (itemid,item_name,total_price,user,qty) values(uuid_to_bin(%s),%s,%s,%s,%s)',[itemid,name,price,session.get('user'),qyt])
        mytdb.commit()
        cursor.close()
        flash('order placed successfully')
        return 'success'
    except razorpay.error.SignatureVerificationError:
        return 'Payment verification failed'  #400'''
@app.route('/orders')
def orders():
    if session.get('user'):
        try:
            cursor=mytdb.cursor(buffered=True)
            cursor.execute('select orderid,bin_to_uuid(itemid),item_name,total_price,user,qty from orders where user=%s',[session.get('user')])
            ordlist=cursor.fetchall()
        except Exception as e:
            print('Error in fetching orders')
            flash('could not fetch orders')
            return redirect(url_for('index'))
        else:
            return render_template('orders.html',ordlist=ordlist)
    return redirect(url_for('userlogin'))
@app.route('/search',methods=['GET','POST'])
def search():
    if request.method=='POST':
        search=request.form['search']
        strg=['A-Za-z0-9']
        pattern=re.compile(f'{strg}',re.IGNORECASE)
        if (pattern.match(search)):
            try:
                cursor=mytdb.cursor(buffered=True)
                cursor.execute('select bin_to_uuid(item_id),item_name,quantity,price,category,image_name from items where item_name like %s or price like %s or category like %s or description like %s',['%'+search+'%','%'+search+'%','%'+search+'%','%'+search+'%'])
                searchdata=cursor.fetchall()
                #cursor.close()
                #return render_template('dashboard.html',sdata=sdata)
            except Exception as e:
                print(f'error to fetch searchdata:{e}')
                flash("can't find anything")
                return redirect(url_for('index'))
            else:
                return render_template('dashboard.html',items_data=searchdata)
        else:
            flash('No data given invalid search')
            return redirect(url_for('index'))
    return render_template('index.html') 
@app.route('/addreview/<itemid>',methods=['GET','POST'])
def addreview(itemid):
    if session.get('user'):
        if request.method=='POST':
            title=request.form['title']
            reviewtext=request.form['review']
            rating=request.form['rate']
            try:
                cursor=mytdb.cursor(buffered=True)
                cursor.execute('insert into reviews(username,itemid,title,review,rating) values(%s uuid_to_bin(%s),%S,%s,%s)',[session.get('user'),itemid,title,reviewtext,rating])
                mytdb.commit()
            except Exception as e:
                print(f'Error in inserting review:{e}')
                flash("can't add a review") 
                return redirect(url_for('description',itemid=itemid))
            else:
                cursor.close()
                flash('review has given')
                return redirect(url_for('description',itemid=itemid))
        return render_template('review.html')    
    else:
        return redirect(url_for('userlogin')) 
@app.route('/contact',methods=['GET','POST'])
def contact():
        return render_template('contact.html')            
if __name__=='main':
    app.run()
