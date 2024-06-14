# ==================imports===================
import sqlite3
import re
from tkinter import *
from tkinter import messagebox
from tkinter.filedialog import askopenfilename
from tkinter.font import Font
from tkinter import ttk
from time import strftime
from PIL import ImageTk, Image
from win32api import GetMonitorInfo, MonitorFromPoint
import logging
from os import makedirs, path, startfile, remove
from shutil import rmtree
from subprocess import run
from json import load, loads
from shutil import copyfile
from os.path import basename
from twilio.rest import Client
from tkcalendar import DateEntry

# ============================================
global root
root = Tk()
style = ttk.Style()
screen_size = (GetMonitorInfo(MonitorFromPoint((0,0))).get("Work")[2], GetMonitorInfo(MonitorFromPoint((0,0))).get("Work")[3])
screen_size = (screen_size[0], screen_size[1])
sub_screen_size = (int(screen_size[0]*0.8), int(screen_size[1]*0.8))
sub_screen_x, sub_screen_y = int((screen_size[0]-sub_screen_size[0])//2), int((screen_size[1]-sub_screen_size[1])//2)

designed_screen_size = (1536, 864)
screen_ratio = (screen_size[0]/designed_screen_size[0], screen_size[1]/designed_screen_size[1])
get_int = lambda x: int(x) if x.isdigit() else ''

################ Fonts #################
large_font = Font(family="Segoe UI", size=int(0.5*(screen_ratio[0]+screen_ratio[1])*20), weight="bold")
medium_font = Font(family="Segoe UI", size=int(0.5*(screen_ratio[0]+screen_ratio[1])*14))
small_font = Font(family="Segoe UI", size=int(0.5*(screen_ratio[0]+screen_ratio[1])*11))

################ Constants #################
scan_info_file = "scan_info.json"
status_d = {
    0: "0\nNot yet detected",
    1: "1\nWaiting for verification",
    2: "2\nNotified detected location to\ncomplainant & nearby police stations",
    3: "3\nVerification Failed"
}
detector_fl, detector_backend, surity = 'face_detector.py', 'opencv', 2

################ Images #################
main_img = Image.open('./assets/main_pg.png')
complaint_img = Image.open('./assets/complaint_pg.png')
refresh_img = Image.open('./assets/refresh.png')

###############################################

with sqlite3.connect("./Database/data.db") as db:
    db.row_factory = sqlite3.Row
    cur = db.cursor()

makedirs("./logs", exist_ok=True)
logging.basicConfig(filename="./logs/app.log", level=logging.ERROR, format='%(asctime)s:%(levelname)s:%(message)s')

format_name = lambda name: name.strip().lower().replace(" and ", " & ").replace("-", " ").replace("_", " ").title().replace(" ", "").replace(".", "").replace(",", "").replace("'", "").replace('"', "")

msng_ppl_columns = ('id', 'name', 'gender', 'age', 'missing_state', 'missing_city', 'pincode', 'missing_date', 'description', 
                    'image', 'complaint_name', 'complaint_phone', 'complaint_address', 'footage_path', 'status')
msng_ppl_col_d = {col: i for i, col in enumerate(msng_ppl_columns)}

################### Common Functions ####################
def resize_image(img, size):
    return ImageTk.PhotoImage(img.resize(size, Image.BICUBIC))

def valid_phone(phn):
    if re.match(r"[6789]\d{9}$", phn):
        return True
    return False

def validate_int(val):
    if val.isdigit():
        return True
    elif val == "":
        return True
    return False

def validate_float(val):
    if val.isdigit():
        return True
    elif val == "":
        return True
    elif val.count('.') == 1 and val.replace('.', '').isdigit():
        return True
    return False

class MainScreen:
    def __init__(self, top=None):
        top.geometry(f"{screen_size[0]}x{screen_size[1]}+0+0")
        top.resizable(0, 0)
        top.title("Missing People Finder")

        root.bind("<F5>", lambda event: self.refresh())
        root.bind("<Control-r>", lambda event: self.refresh())

        self.label1 = Label(root)
        self.label1.place(relx=0.0, rely=0.0, width=screen_size[0], height=screen_size[1])
        img = resize_image(main_img, screen_size)
        self.label1.configure(image=img)
        self.label1.image = img

        self.verification_msg_label = Label(root)
        self.verification_msg_label.place(relx=0.275, rely=0.11, width=screen_ratio[0]*300, height=screen_ratio[1]*30)
        self.verification_msg_label.configure(
            font=Font(family="Segoe UI", size=int(0.5*(screen_ratio[0]+screen_ratio[1])*16), weight="bold"),
            background="#FFFFFF", anchor=W
        )
        self.update_verification_count()
        
        self.clock = Label(root)
        self.clock.place(relx=0.1695, rely=0.1575, width=screen_ratio[0]*105, height=screen_ratio[1]*40)
        self.clock.configure(
            font=Font(family="Segoe UI", size=int(0.5*(screen_ratio[0]+screen_ratio[1])*14)),
            foreground="#000000",
            background="#FFFFFF"
        )

        self.date_label = Label(root)
        self.date_label.place(relx=0.065, rely=0.1575, width=screen_ratio[0]*100, height=screen_ratio[1]*40)
        self.date_label.configure(
            font=Font(family="Segoe UI", size=int(0.5*(screen_ratio[0]+screen_ratio[1])*14)),
            foreground="#000000",
            background="#FFFFFF"
        )

        self.people_key_entry = Entry(root)
        self.people_key_entry.place(relx=0.043, rely=0.337, width=screen_ratio[0]*300, height=screen_ratio[1]*40)
        self.people_key_entry.configure(font=medium_font, relief="flat")
        self.people_key_entry.bind("<Return>", lambda event: self.search_missing_people())

        self.people_search_btn = Button(root)
        self.people_search_btn.place(relx=0.1, rely=0.407, width=screen_ratio[0]*126, height=screen_ratio[1]*35)
        self.people_search_btn.configure(background="#9AD1F9", borderwidth="0", cursor="hand2", text="Search", activebackground="#9AD1F9", 
                                          font=Font(family="Segoe UI", size=int(0.5*(screen_ratio[0]+screen_ratio[1])*16), weight="bold"), 
                                          command=self.search_missing_people)
        
        self.add_missing_person_btn = Button(root)
        self.add_missing_person_btn.place(relx=0.06, rely=0.5085, width=screen_ratio[0]*250, height=screen_ratio[1]*47)
        self.add_missing_person_btn.configure(background="#9AD1F9", borderwidth="0", cursor="hand2", text="Add New", activebackground="#9AD1F9",
                                        font=Font(family="Segoe UI", size=int(0.5*(screen_ratio[0]+screen_ratio[1])*16), weight="bold"),
                                        command=self.add_missing_person)

        self.match_btn = Button(root)
        self.match_btn.place(relx=0.0435, rely=0.715, width=screen_ratio[0]*120, height=screen_ratio[1]*45)
        self.match_btn.configure(background="#56B235", borderwidth="0", cursor="hand2", text="Match", activebackground="#56B235", 
                                          font=Font(family="Segoe UI", size=int(0.5*(screen_ratio[0]+screen_ratio[1])*16), weight="bold"), 
                                          command=self.match)
        
        self.no_match_btn = Button(root)
        self.no_match_btn.place(relx=0.16, rely=0.715, width=screen_ratio[0]*120, height=screen_ratio[1]*45)
        self.no_match_btn.configure(background="#F77A39", borderwidth="0", cursor="hand2", text="No Match", activebackground="#F77A39", 
                                          font=Font(family="Segoe UI", size=int(0.5*(screen_ratio[0]+screen_ratio[1])*16), weight="bold"), 
                                          command=self.no_match)

        self.refresh_btn = Button(root)
        self.refresh_btn.place(relx=0.082, rely=0.857, width=screen_ratio[0]*180, height=screen_ratio[1]*60)
        img = resize_image(refresh_img, (int(screen_ratio[0]*180), int(screen_ratio[1]*60)))
        self.refresh_btn.configure(image=img, borderwidth="0", cursor="hand2", background="#ffffff", command=self.refresh)
        self.refresh_btn.image = img
        # self.refresh_btn.configure(background="#9AD1F9", borderwidth="0", cursor="hand2", text="Exit", activebackground="#9AD1F9",
        #                         font=Font(family="Segoe UI", size=int(0.5*(screen_ratio[0]+screen_ratio[1])*16), weight="bold"),
        #                         command=self.refresh)

        style.theme_use("clam")
        style.configure("tree.Treeview", highlightthickness=0, bd=0, font=small_font) # Modify the font of the body
        style.configure("tree.Treeview.Heading", font=("Segoe UI Semibold", int(0.5*(screen_ratio[0]+screen_ratio[1])*14)), background='#9AD1F9', foreground='black', borderwidth=0) # Modify the font of the headings
        style.layout("tree.Treeview", [('tree.Treeview.treearea', {'sticky': 'nswe'})]) # Remove the borders
        style.configure("tree.Treeview", rowheight=int(screen_ratio[0]*90))
        self.tree = ttk.Treeview(root, style="tree.Treeview")
        self.scrollbarx = Scrollbar(root, orient=HORIZONTAL)
        self.scrollbary = Scrollbar(root, orient=VERTICAL)
        self.scrollbarx.configure(command=self.tree.xview)
        self.scrollbary.configure(command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.scrollbary.set, xscrollcommand=self.scrollbarx.set)

        self.tree.place(relx=0.28, rely=0.164, width=screen_ratio[0]*990, height=screen_ratio[1]*610)
        self.scrollbary.place(relx=0.954, rely=0.203, width=screen_ratio[0]*22, height=screen_ratio[1]*548)
        self.scrollbarx.place(relx=0.28, rely=0.9, width=screen_ratio[0]*990, height=screen_ratio[1]*22)

        # self.tree.configure(columns=("PID", "Missing Person Details", "Complainant Details", "Status"))
        self.tree["columns"] = ("pid", "missing_person_details", "complainant_details", "status")

        self.tree_d = {col: i for i, col in enumerate(self.tree["columns"])}
        self.tree.heading("pid", text="PID", anchor=W)
        self.tree.heading("missing_person_details", text="Missing Person Details", anchor=W)
        self.tree.heading("complainant_details", text="Complainant Details", anchor=W)
        self.tree.heading("status", text="Status", anchor=W)

        self.tree['show'] = 'headings'
        self.tree.column("pid", width=int(screen_ratio[0]*80), anchor=W)
        self.tree.column("missing_person_details", width=int(screen_ratio[0]*300), anchor=W)
        self.tree.column("complainant_details", width=int(screen_ratio[0]*270), anchor=W)
        self.tree.column("status", width=int(screen_ratio[0]*180), anchor=W)

        self.tree.bind("<Delete>", lambda event: self.delete_missing_people())
        self.tree.bind("<Double-Button-1>", self.display_images_folder)

        self.DisplayData(cur.execute("SELECT * FROM missing_people").fetchall())

        # check if any of the missing person has status as 3 (found), if yes, then delete the person from the database
        cur.execute("SELECT * FROM missing_people WHERE status=3")
        results = cur.fetchall()
        if len(results) > 0:
            sure = messagebox.askyesno("Warning", "Some of the missing people have been found. Do you want to delete them?", parent=root)
            if sure:
                for result in results:
                    cur.execute("DELETE FROM missing_people WHERE id=?", (result["id"],))
                db.commit()
                messagebox.showinfo("Success!!", "Deleted successfully.", parent=root)
                self.DisplayData(cur.execute("SELECT * FROM missing_people").fetchall())

        self.refresh()

    def add_missing_person(self):

        global mp_add
        global add_missing_person_pg
        mp_add = Toplevel()
        add_missing_person_pg = AddMissingPerson(mp_add)
        mp_add.protocol("WM_DELETE_WINDOW", lambda: self.exit_custom(mp_add))
        add_missing_person_pg.m_fullname_entry.focus()
        mp_add.mainloop()
    
    def send__sms(self, to, body):

        to = f"+91{to}" if len(str(to)) == 10 else f"+{to}"
        tw_creds = loads(open('creds.json').read())["twilio"]

        account_sid, auth_token = tw_creds["sid"], tw_creds["token"]
        client = Client(account_sid, auth_token)

        message = client.messages.create(
            from_=tw_creds['from_'],
            body=body,
            to=to
        )
        return message.sid

    def match(self):

        if len(self.tree.selection()) == 0:
            return
        try:
            # fetch pid based on selection on the tree
            selected_item = self.tree.selection()[0]
            pid = self.tree.item(selected_item)["values"][self.tree_d["pid"]]

            # fetch the details of the person
            fetch = cur.execute("SELECT * FROM missing_people WHERE id=?", (pid,)).fetchone()
            msg_tmplt = f"Hello {fetch['complaint_name'].replace('_', ' ').title()},\n\nWe have located the missing person {fetch['name'].replace('_', ' ').title()}, please visit us to verify.\n\nThank you."
            response = self.send__sms(fetch['complaint_phone'], msg_tmplt)
            if response:
                cur.execute("UPDATE missing_people SET status=2 WHERE id=?", (pid,))
                db.commit()
                self.update_verification_count()
                messagebox.showinfo("Success!!", "Message sent successfully.", parent=root)
                self.refresh()
            else:
                messagebox.showinfo("Error!!", "Message could not be sent.", parent=root)
        except Exception as e:
            logging.error(f"Error: {e}")
            messagebox.showinfo("Error!!", "Something went wrong.", parent=root)

    def no_match(self):

        if len(self.tree.selection()) == 0:
            return
        
        selected_item = self.tree.selection()[0]
        pid = self.tree.item(selected_item)["values"][self.tree_d["pid"]]

        # fetch the details of the person
        cur.execute("UPDATE missing_people SET status=3 WHERE id=?", (pid,))
        db.commit()
        self.update_verification_count()
        messagebox.showinfo("Success!!", "Updated database successfully.", parent=root)
        self.refresh()

    def display_images_folder(self, event):
        selected_item = self.tree.selection()[0]
        pid = self.tree.item(selected_item)["values"][self.tree_d["pid"]]
        pid_status = self.tree.item(selected_item)["values"][self.tree_d["status"]].split("\n")[0]
        if pid_status == "0":
            messagebox.showinfo("Error!!", "This person has not been detected yet.", parent=root)
            return
        elif pid_status == "2":
            messagebox.showinfo("Error!!", "This person has already been verified.", parent=root)
            return

        fetch = cur.execute("SELECT * FROM missing_people WHERE id=?", (pid,)).fetchone()
        fold_path = f"./found/{pid}/{basename(fetch['footage_path']).split('.')[0]}"
        copyfile(f"./data/{pid}.jpg", f"{fold_path}/0.jpg")
        # put all the info in a text file
        with open(f"{fold_path}/info.txt", 'w') as f:
            f.write(f"Name: {fetch['name'].replace('_', ' ').title()}\nGender: {fetch['gender']}\nAge: {fetch['age']}\nMissing From: {fetch['missing_date']}\nPlace: {fetch['missing_city']}-{fetch['pincode']}, {fetch['missing_state']}\n\nDescription: {fetch['description']}")
        startfile(path.abspath(fold_path))

    def update_verification_count(self):
        cur.execute("SELECT COUNT(*) FROM missing_people WHERE status=1")
        ver_count = cur.fetchone()[0]
        if ver_count == 0:
            self.verification_msg_label.configure(text="Verification Pending: 0", foreground="Green")
        else:
            self.verification_msg_label.configure(text=f"Verification Pending: {ver_count}", foreground="Red")

    def DisplayData(self, data_lst):
        self.tree.delete(*self.tree.get_children())
        for data in data_lst:
            # msng_prsn_dtls = f"Name: {data["name"]}\nGender: {data["gender"]}  Age: {data['age']}\nMissing From: {data['missing_date']}\nCity: {data['missing_city']} State: {data['missing_state']}"
            msng_prsn_dtls = f"Name: {data['name'].replace('_', ' ').title()}\nGender/Age: {data['gender']}/{data['age']}\nMissing From: {data['missing_date']}\nLast Seen at: {data['missing_city']}-{data['pincode']}, {data['missing_state']}"
            complnt_dtls = f"Name: {data['complaint_name'].replace('_', ' ').title()}\nPhone: {data['complaint_phone']}\nAddress: {data['complaint_address']}"
            self.tree.insert("", "end", values=(data["id"], msng_prsn_dtls, complnt_dtls, status_d[data["status"]]))    

    def search_missing_people(self):

        if self.people_key_entry.get() == "":
            self.DisplayData(cur.execute("SELECT * FROM missing_people").fetchall())
            return
        
        cur.execute(f"SELECT * FROM missing_people WHERE name LIKE '{self.people_key_entry.get()}%' OR complaint_name LIKE '{self.people_key_entry.get()}%' OR status LIKE '{self.people_key_entry.get()}%' OR \
                    complaint_phone LIKE '{self.people_key_entry.get()}%' OR missing_city LIKE '{self.people_key_entry.get()}%' OR missing_state LIKE '{self.people_key_entry.get()}%'")
        results = cur.fetchall()
        if len(results) > 0:
            self.DisplayData(results)
        else:
            messagebox.showinfo("Error!!", "No such missing person found.", parent=root)

    def delete_missing_people(self):
        
        ids = self.tree.selection()
        if len(ids) == 0:
            return
        sure = messagebox.askyesno("Delete", "Are you sure you want to delete these product(s)?", parent=root)
        if sure == True:
            for i in ids: 

                # also remove the images from the data folder
                pid = self.tree.item(i)["values"][self.tree_d["pid"]] 
                if path.isfile(f"./data/{pid}.jpg"):
                    remove(f"./data/{pid}.jpg")
                if path.isdir(f"./found/{pid}"):
                    rmtree(f"./found/{pid}")

                cur.execute("DELETE FROM missing_people WHERE id=?", (pid,))
                self.tree.delete(i) 

            db.commit()
            self.refresh()


    def dtime(self):
        # string = strftime("%I:%M:%S %p")
        self.date_label.config(text=strftime("%d-%m-%Y"))
        self.clock.config(text=strftime("%I:%M:%S %p"))
        self.clock.after(1000, self.dtime)

    def refresh(self):
        # update table based on the info in scan_info_file
        with open(scan_info_file, 'r') as f:
            scan_info = load(f)
        try:
            cur.execute(f"UPDATE missing_people SET status=1 WHERE id IN ({','.join(scan_info['for_verification_pids'].keys())}) AND status=0")
            db.commit()
        except Exception as e:
            logging.error(f"Error: {e}")
        self.DisplayData(cur.execute("SELECT * FROM missing_people").fetchall())
        self.update_verification_count()

    def Exit(self):
        sure = messagebox.askyesno("Exit","Are you sure you want to exit?", parent=root)
        if sure == True:
            root.destroy()

    def exit_custom(self, parent):
        sure = messagebox.askyesno("Exit","Are you sure you want to exit?", parent=parent)
        if sure == True:
            parent.destroy()
            root.deiconify()
            self.DisplayData(cur.execute("SELECT * FROM missing_people").fetchall())

class AddMissingPerson:
    def __init__(self, top=None):
        top.geometry(f"{sub_screen_size[0]}x{sub_screen_size[1]}+{sub_screen_x}+{sub_screen_y}")
        top.resizable(0, 0)
        top.title("Add Missing Person")

        self.label1 = Label(mp_add)
        self.label1.place(relx=0.0, rely=0.0, width= sub_screen_size[0], height=sub_screen_size[1])
        img = resize_image(complaint_img, sub_screen_size)
        self.label1.configure(image=img)
        self.label1.image = img

        self.int_validator = mp_add.register(validate_int)

        self.m_fullname_entry = Entry(mp_add)
        self.m_fullname_entry.place(relx=0.075, rely=0.283, width=screen_ratio[0]*320, height=screen_ratio[1]*33)
        self.m_fullname_entry.configure(font=medium_font, relief="flat")

        style.theme_use("clam")
        style.map("desg_options.TCombobox", fieldbackground=[("readonly", "#ffffff")], foreground=[("readonly", "#000000")], selectforeground=[("readonly", "black")], 
                    selectbackground=[("readonly", "#ffffff")], background=[("readonly", "#ffffff")], bordercolor=[("readonly", "#ffffff")])
        self.m_gender = StringVar()
        self.m_gender.set("Male")
        self.m_gender = ttk.Combobox(mp_add, textvariable=self.m_gender,values=["Male", "Female", "Other"], state="readonly", style="desg_options.TCombobox")
        self.m_gender.place(relx=0.075, rely=0.413, width=screen_ratio[0]*150, height=screen_ratio[1]*33)
        self.m_gender.configure(font=medium_font)

        self.m_age_entry = Entry(mp_add)
        self.m_age_entry.place(relx=0.21, rely=0.413, width=screen_ratio[0]*150, height=screen_ratio[1]*33)
        self.m_age_entry.configure(font=medium_font, relief="flat", validate="key", validatecommand=(self.int_validator, "%P"))

        self.m_state_entry = Entry(mp_add)
        self.m_state_entry.place(relx=0.075, rely=0.543, width=screen_ratio[0]*150, height=screen_ratio[1]*33)
        self.m_state_entry.configure(font=medium_font, relief="flat")

        self.m_city_entry = Entry(mp_add)
        self.m_city_entry.place(relx=0.21, rely=0.543, width=screen_ratio[0]*150, height=screen_ratio[1]*33)
        self.m_city_entry.configure(font=medium_font, relief="flat")

        self.m_pincode_entry = Entry(mp_add)
        self.m_pincode_entry.place(relx=0.075, rely=0.673, width=screen_ratio[0]*150, height=screen_ratio[1]*33)
        self.m_pincode_entry.configure(font=medium_font, relief="flat", validate="key", validatecommand=(self.int_validator, "%P"))

        style.configure('my.DateEntry', fieldbackground='white', background='white', foreground='black', arrowcolor='black',
                bordercolor='white')
        self.m_missing_date_entry = DateEntry(mp_add, date_pattern="dd/mm/yyyy", style="my.DateEntry")
        self.m_missing_date_entry.place(relx=0.21, rely=0.673, width=screen_ratio[0]*150, height=screen_ratio[1]*33)
        self.m_missing_date_entry.configure(font=medium_font)

        self.m_description_entry = Entry(mp_add)
        self.m_description_entry.place(relx=0.075, rely=0.808, width=screen_ratio[0]*320, height=screen_ratio[1]*33)
        self.m_description_entry.configure(font=medium_font, relief="flat")

        self.c_fullname_entry = Entry(mp_add)
        self.c_fullname_entry.place(relx=0.374, rely=0.283, width=screen_ratio[0]*320, height=screen_ratio[1]*33)
        self.c_fullname_entry.configure(font=medium_font, relief="flat")

        self.c_relation_entry = Entry(mp_add)
        self.c_relation_entry.place(relx=0.374, rely=0.413, width=screen_ratio[0]*320, height=screen_ratio[1]*33)
        self.c_relation_entry.configure(font=medium_font, relief="flat")

        self.c_phone_entry = Entry(mp_add)
        self.c_phone_entry.place(relx=0.374, rely=0.543, width=screen_ratio[0]*320, height=screen_ratio[1]*33)
        self.c_phone_entry.configure(font=medium_font, relief="flat", validate="key", validatecommand=(self.int_validator, "%P"))

        self.c_address1_entry = Entry(mp_add)
        self.c_address1_entry.place(relx=0.374, rely=0.673, width=screen_ratio[0]*320, height=screen_ratio[1]*33)
        self.c_address1_entry.configure(font=medium_font, relief="flat")

        self.c_address2_entry = Entry(mp_add)
        self.c_address2_entry.place(relx=0.374, rely=0.808, width=screen_ratio[0]*320, height=screen_ratio[1]*33)
        self.c_address2_entry.configure(font=medium_font, relief="flat")

        self.recent_photo_entry = Entry(mp_add)
        self.recent_photo_entry.place(relx=0.673, rely=0.413, width=screen_ratio[0]*320, height=screen_ratio[1]*33)
        self.recent_photo_entry.configure(font=small_font, relief="flat")
        self.recent_photo_entry.bind("<Button-1>", self.onClick_recent_photo_entry)

        self.footage_entry = Entry(mp_add)
        self.footage_entry.place(relx=0.673, rely=0.543, width=screen_ratio[0]*320, height=screen_ratio[1]*33)
        self.footage_entry.configure(font=small_font, relief="flat")
        self.footage_entry.bind("<Button-1>", self.onClick_footage_entry)

        self.add_btn = Button(mp_add)
        self.add_btn.place(relx=0.68, rely=0.7275, width=screen_ratio[0]*140, height=screen_ratio[1]*40)
        self.add_btn.configure(background="#9AD1F9", borderwidth="0", cursor="hand2", text="Add", activebackground="#9AD1F9", foreground='green',
                                          font=Font(family="Segoe UI", size=int(0.5*(screen_ratio[0]+screen_ratio[1])*16), weight="bold"), 
                                          command=self.add_missing_person)
        
        self.cancel_btn = Button(mp_add)
        self.cancel_btn.place(relx=0.826, rely=0.7275, width=screen_ratio[0]*140, height=screen_ratio[1]*40)
        self.cancel_btn.configure(background="#9AD1F9", borderwidth="0", cursor="hand2", text="Cancel", activebackground="#F77A39", foreground='red', 
                                          font=Font(family="Segoe UI", size=int(0.5*(screen_ratio[0]+screen_ratio[1])*16), weight="bold"),
                                          command=lambda: mp_add.destroy())
        

    def onClick_recent_photo_entry(self, event):
        self.recent_photo_entry.delete(0, END)
        self.recent_photo_entry.insert(0, askopenfilename(parent=mp_add, title="Choose a file", filetypes=[("Image Files", "*.jpg *.jpeg *.png")]))
    
    def onClick_footage_entry(self, event):
        self.footage_entry.delete(0, END)
        self.footage_entry.insert(0, askopenfilename(parent=mp_add, title="Choose a file", filetypes=[("Video Files", "*.mp4")]))

    def clearr(self):

        for widget in mp_add.winfo_children():
            if isinstance(widget, Entry):
                widget.delete(0, END)
        self.m_fullname_entry.focus_set()

    def copyfiles(self, recent_photo_path):

        pid = cur.execute("SELECT MAX(id) FROM missing_people").fetchone()[0]           # pid will never be None as we are calling this function after inserting the data

        img_ext = recent_photo_path.split('.')[-1]
        img_fl_path = f"./data/{pid}.{img_ext}"
        copyfile(recent_photo_path, f"{img_fl_path}")
        # also update the image path in the database
        cur.execute(f"UPDATE missing_people SET image_f='{img_fl_path}' WHERE id={pid}")

    def start_detection(self, footage_path):

        # use psutil and check if the process is already running - future implementation
        logs_fl = f"./logs/{basename(footage_path).split('.')[0]}.log"
        run(f'start /B python {detector_fl} -fp "{footage_path}" -db {detector_backend} -s {surity} > {logs_fl} 2>&1', shell=True)

    def add_missing_person(self):

        m_fullname, m_gender, m_age = self.m_fullname_entry.get().strip().replace(" ", "_"), self.m_gender.get(), get_int(self.m_age_entry.get())
        m_state, m_city, m_pincode = self.m_state_entry.get().strip().replace(" ", "_"), self.m_city_entry.get().strip().replace(" ", "_"), get_int(self.m_pincode_entry.get())
        m_missing_date, m_description = self.m_missing_date_entry.get(), self.m_description_entry.get().strip()
        c_fullname, c_relation = self.c_fullname_entry.get().strip().replace(" ", "_"), self.c_relation_entry.get().strip()
        c_phone, c_address1, c_address2 = get_int(self.c_phone_entry.get()), self.c_address1_entry.get().strip(), self.c_address2_entry.get().strip()
        recent_photo_path, footage_path = self.recent_photo_entry.get().strip(), self.footage_entry.get().strip()

        required_fields = [m_fullname, m_gender, m_age, m_state, m_city, m_pincode, m_missing_date, m_description, c_fullname, c_relation, c_phone, c_address1, c_address2, recent_photo_path]
        if "" in required_fields:
            messagebox.showinfo("Error!!", "Please fill all required fields.", parent=mp_add)
            return
        
        if not valid_phone(str(c_phone)):
            messagebox.showinfo("Error!!", "Invalid phone number.", parent=mp_add)
            return
        
        if not path.exists(recent_photo_path):
            messagebox.showinfo("Error!!", "Invalid recent photo path.", parent=mp_add)
            return
        
        if not path.exists(footage_path):
            messagebox.showinfo("Error!!", "Invalid footage path.", parent=mp_add)
            return
        
        address = f"{c_address1}\n{c_address2}"

        try:
            cur.execute(f"INSERT INTO missing_people (name, gender, age, missing_state, missing_city, pincode, missing_date, description, image_f, complaint_name, complaint_phone, complaint_address, footage_path, status) \
                        VALUES ('{m_fullname}', '{m_gender}', {m_age}, '{m_state}', '{m_city}', {m_pincode}, '{m_missing_date}', '{m_description}', '{recent_photo_path}', '{c_fullname}', {c_phone}, '{address}', '{footage_path}', 0)")
            db.commit()
            # copy the image to the data folder
            self.copyfiles(recent_photo_path)
            # start the detection process
            self.start_detection(footage_path)
            messagebox.showinfo("Success!!", "Added successfully.", parent=mp_add)
            self.clearr()
        except Exception as e:
            logging.error(f"Error: {e}")
            messagebox.showinfo("Error!!", "Something went wrong.", parent=mp_add)
            return

# check if is root window
if __name__ == "__main__":
    global main_pg
    main_pg = MainScreen(root)
    main_pg.dtime()
    root.protocol("WM_DELETE_WINDOW", lambda: main_pg.Exit())
    root.mainloop()

