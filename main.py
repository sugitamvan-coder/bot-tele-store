# ==========================================================
#   KREASI DIGITAL Z — FINAL BUILD + ADMIN DASHBOARD (A)
#   FINAL — CORE SYSTEM + USER MENU + PAGINATION (RAPIH)
#   Part 1 + Part 2: Deposit + Admin Panel (w/ Pagination)
# ==========================================================

import os
import json
from datetime import datetime
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
    InputFile
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, CallbackContext, filters
)

# ===================== CONFIG ============================

OWNER_ID = 7576468867
BOT_TOKEN = "8540605643:AAF6vQXv5GTJhhXyQvpHSX0WnNnLpbe4gNU"

# JSON FILES
produk_file = "produk.json"
saldo_file = "saldo.json"
riwayat_file = "riwayat.json"
statistik_file = "statistik.json"
deposit_file = "pending_deposit.json"

# QRIS IMAGE
QRIS_IMAGE_PATH = "qris.png"

# PAGINATION
PRODUK_PER_HALAMAN = 5
ADMIN_ITEMS_PER_PAGE = 10   # ✅ permintaan: 10 data per halaman


# ====================================
#             JSON HELPERS
# ====================================

def load_json(path):
    if not os.path.exists(path):
        if path == produk_file:
            with open(path, "w") as f:
                json.dump({}, f)
        else:
            with open(path, "w") as f:
                json.dump([], f)
    with open(path, "r") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


# ==========================================================
#                    STATISTIK HELPER
# ==========================================================

def update_statistik(jumlah_transaksi, total_pendapatan):
    statistik = load_json(statistik_file)
    if not isinstance(statistik, dict):
        statistik = {"total_transaksi": 0, "total_pendapatan": 0}
    statistik["total_transaksi"] += jumlah_transaksi
    statistik["total_pendapatan"] += total_pendapatan
    save_json(statistik_file, statistik)


# ==========================================================
#                     RIWAYAT HELPER
# ==========================================================

def add_riwayat(user_id, jenis, keterangan, jumlah):
    riwayat = load_json(riwayat_file)
    if not isinstance(riwayat, list):
        riwayat = []
    riwayat.append({
        "user_id": user_id,
        "jenis": jenis,
        "keterangan": keterangan,
        "jumlah": jumlah,
        "waktu": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    save_json(riwayat_file, riwayat)


# ==========================================================
#               UI HELPERS (NAV & LABEL RANGE)
# ==========================================================

def build_nav_row(prefix, page, total_pages):
    """
    Membuat baris navigasi: ⬅️ | 📄 x/y | ➡️
    prefix: string callback prefix, mis. 'list_produk', 'admin_riwayat', 'admin_pending'
    """
    nav_row = []
    if total_pages < 1:
        total_pages = 1
    if page < 1:
        page = 1
    if page > total_pages:
        page = total_pages

    if page > 1:
        nav_row.append(InlineKeyboardButton("⬅️ Sebelumnya", callback_data=f"{prefix}_page_{page-1}"))
    nav_row.append(InlineKeyboardButton(f"📄 {page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton("➡️ Selanjutnya", callback_data=f"{prefix}_page_{page+1}"))
    return nav_row


def label_range(start_idx, count_on_page, total):
    if total == 0:
        return "Menampilkan 0 dari 0 total"
    start_display = start_idx + 1
    end_display = start_idx + count_on_page
    return f"Menampilkan {start_display}–{end_display} dari {total} total"


# ==========================================================
#                    MENU UTAMA / START
# ==========================================================

def build_main_keyboard(user_id=None):
    keyboard = [
        [InlineKeyboardButton("🛒 List Produk", callback_data="list_produk")],
        [InlineKeyboardButton("💰 Deposit Saldo", callback_data="deposit")],
        [InlineKeyboardButton("📦 Cek Stok", callback_data="cek_stok")],
    ]
    if user_id == OWNER_ID:
        keyboard.append([InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin_panel")])
    return InlineKeyboardMarkup(keyboard)


async def send_main_menu(context: CallbackContext, chat_id, user):
    saldo = load_json(saldo_file)
    user_saldo = saldo.get(str(user.id), 0)
    text = (
        f"👋 Halo, *{user.first_name}*, Mohon Sebelum Transaksi Untuk Isi Saldo Terlebih Dahulu!!\n\n"
        f"💰 Saldo kamu saat ini: *Rp{user_saldo:,}*\n\n"
        "Silakan pilih menu di bawah ini:"
    )
    await context.bot.send_message(
        chat_id=chat_id, text=text, parse_mode="Markdown",
        reply_markup=build_main_keyboard(user.id)
    )


async def start(update: Update, context: CallbackContext):
    user = update.effective_user
    await send_main_menu(context, update.effective_chat.id, user)


# ==========================================================
#                 LIST PRODUK (PAGINATION)
# ==========================================================

async def handle_list_produk(update: Update, context: CallbackContext):
    q = update.callback_query
    data = q.data
    page = 1
    if data.startswith("list_produk_page_"):
        try:
            page = int(data.split("_")[-1])
        except:
            page = 1

    produk = load_json(produk_file)
    if not produk:
        return await q.edit_message_text("Belum ada produk yang tersedia.")

    produk_items = list(produk.items())
    total_produk = len(produk_items)
    total_halaman = (total_produk + PRODUK_PER_HALAMAN - 1) // PRODUK_PER_HALAMAN or 1

    if page < 1:
        page = 1
    if page > total_halaman:
        page = total_halaman

    start_idx = (page - 1) * PRODUK_PER_HALAMAN
    end_idx = start_idx + PRODUK_PER_HALAMAN
    produk_page = produk_items[start_idx:end_idx]

    text = f"🛒 *DAFTAR PRODUK* (Halaman {page}/{total_halaman})\n\n"
    keyboard = []

    # ==========================================================
#                   LIST PRODUK (DIPERBARUI)
# ==========================================================

async def handle_list_produk(update: Update, context: CallbackContext):
    q = update.callback_query
    data = q.data
    page = 1

    if data.startswith("list_produk_page_"):
        try:
            page = int(data.split("_")[-1])
        except:
            page = 1

    produk = load_json(produk_file)
    if not produk:
        return await q.edit_message_text("❌ Belum ada produk yang tersedia.")

    produk_items = list(produk.items())
    total_produk = len(produk_items)
    total_halaman = (total_produk + PRODUK_PER_HALAMAN - 1) // PRODUK_PER_HALAMAN

    start_idx = (page - 1) * PRODUK_PER_HALAMAN
    end_idx = start_idx + PRODUK_PER_HALAMAN
    produk_page = produk_items[start_idx:end_idx]

    text = (
        f"🏬 *KREASI DIGITAL Z STORE*\n"
        f"👨‍💻 *Author : @f0rlemz* [SugiKode] \n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📄 Halaman *{page} / {total_halaman}*\n"
        f"🕒 {datetime.now().strftime('%I:%M %p')}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    )

    keyboard = []
    for pid, item in produk_page:
        text += (
            f"✨ *{item['nama'].upper()}*\n"
            f"💰 Harga: *Rp{item['harga']:,}*\n"
            f"📦 Stok: *{item['stok']}*\n"
            f"───────────────\n"
        )
        keyboard.append([InlineKeyboardButton(f"🛒 {item['nama']}", callback_data=pid)])

    keyboard.append(build_nav_row("list_produk", page, total_halaman))
    keyboard.append([InlineKeyboardButton("🔙 Kembali ke Menu", callback_data="main_menu")])

    await q.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

# ==========================================================
#                   DETAIL PRODUK (DIPERBARUI)
# ==========================================================

async def handle_produk_detail(update: Update, context: CallbackContext):
    q = update.callback_query
    pid = q.data
    produk = load_json(produk_file)
    item = produk.get(pid)

    if not item:
        return await q.edit_message_text("❌ Produk tidak ditemukan.")

    context.user_data["selected_product"] = pid
    context.user_data["qty"] = 1

    text = (
        f"🛍️ *DETAIL PRODUK*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 Nama Produk: *{item['nama']}*\n"
        f"💰 Harga Satuan: *Rp{item['harga']:,}*\n"
        f"📦 Stok Tersedia: *{item['stok']}*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Atur jumlah yang ingin dibeli di bawah ini 👇"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➖", callback_data="qty_minus"),
            InlineKeyboardButton("1", callback_data="noop"),
            InlineKeyboardButton("➕", callback_data="qty_plus"),
        ],
        [InlineKeyboardButton("🛒 Beli Sekarang", callback_data="buy_now")],
        [InlineKeyboardButton("🔙 Kembali ke Daftar", callback_data="list_produk")],
    ])

    await q.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)


    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➖", callback_data="qty_minus"),
            InlineKeyboardButton(f"Qty: {context.user_data['qty']}", callback_data="noop"),
            InlineKeyboardButton("➕", callback_data="qty_plus")
        ],
        [InlineKeyboardButton("✅ Konfirmasi", callback_data="confirm_order")],
        [InlineKeyboardButton("🔙 Kembali", callback_data="list_produk")],
    ])

    await q.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)


# ==========================================================
#                    QTY HANDLER
# ==========================================================

def build_konfirmasi_text(item, jumlah):
    return (
        "KONFIRMASI PESANAN 🛒\n"
        "╭──────────────────────────────╮\n"
        f"┊ • Produk: {item['nama']}\n"
        f"┊ • Variasi: {item['akun_list'][0]['tipe'] if item.get('akun_list') else '-'}\n"
        f"┊ • Harga satuan: Rp{item['harga']:,}\n"
        f"┊ • Stok tersedia: {item['stok']}\n"
        "├──────────────────────────────┤\n"
        f"┊ • Jumlah Pesanan: x{jumlah}\n"
        f"┊ • Total Pembayaran: Rp{jumlah * item['harga']:,}\n"
        "╰──────────────────────────────╯"
    )


async def handle_qty_plus(update: Update, context: CallbackContext):
    q = update.callback_query
    pid = context.user_data.get("selected_product")

    produk = load_json(produk_file)
    item = produk.get(pid)

    qty = context.user_data.get("qty", 1)
    if qty < item["stok"]:
        qty += 1
    context.user_data["qty"] = qty

    text = build_konfirmasi_text(item, qty)

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➖", callback_data="qty_minus"),
            InlineKeyboardButton(f"Qty: {qty}", callback_data="noop"),
            InlineKeyboardButton("➕", callback_data="qty_plus")
        ],
        [InlineKeyboardButton("✅ Konfirmasi", callback_data="confirm_order")],
        [InlineKeyboardButton("🔙 Kembali", callback_data="list_produk")]
    ])

    await q.edit_message_text(text, reply_markup=keyboard)


async def handle_qty_minus(update: Update, context: CallbackContext):
    q = update.callback_query
    pid = context.user_data.get("selected_product")

    produk = load_json(produk_file)
    item = produk.get(pid)

    qty = context.user_data.get("qty", 1)
    if qty > 1:
        qty -= 1
    context.user_data["qty"] = qty

    text = build_konfirmasi_text(item, qty)

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➖", callback_data="qty_minus"),
            InlineKeyboardButton(f"Qty: {qty}", callback_data="noop"),
            InlineKeyboardButton("➕", callback_data="qty_plus")
        ],
        [InlineKeyboardButton("✅ Konfirmasi", callback_data="confirm_order")],
        [InlineKeyboardButton("🔙 Kembali", callback_data="list_produk")]
    ])

    await q.edit_message_text(text, reply_markup=keyboard)


# ==========================================================
#              KONFIRMASI ORDER / PEMBELIAN
# ==========================================================

async def handle_confirm_order(update: Update, context: CallbackContext):
    q = update.callback_query
    user = q.from_user
    uid = user.id

    pid = context.user_data.get("selected_product")
    jumlah = context.user_data.get("qty", 1)

    produk = load_json(produk_file)
    saldo = load_json(saldo_file)

    item = produk.get(pid)
    if not item:
        return await q.edit_message_text("❌ Produk tidak ditemukan.")

    total = jumlah * item["harga"]
    user_saldo = saldo.get(str(uid), 0)

    if user_saldo < total:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💰 Deposit Saldo", callback_data="deposit")],
            [InlineKeyboardButton("🔙 Kembali", callback_data="list_produk")]
        ])
        return await q.edit_message_text(
            "❌ *Saldo tidak cukup!* Silakan deposit dahulu.",
            parse_mode="Markdown",
            reply_markup=keyboard
        )

    if item["stok"] < jumlah or len(item.get("akun_list", [])) < jumlah:
        return await q.edit_message_text("❌ Stok / akun tidak mencukupi!")

    # Kurangi saldo & stok
    saldo[str(uid)] = user_saldo - total
    item["stok"] -= jumlah

    akun_terpakai = item["akun_list"][:jumlah]
    item["akun_list"] = item["akun_list"][jumlah:]
    produk[pid] = item

    save_json(saldo_file, saldo)
    save_json(produk_file, produk)
    add_riwayat(uid, "BELI", f"{item['nama']} x{jumlah}", total)

    # kirim file akun
    os.makedirs("akun_dikirim", exist_ok=True)
    file_path = f"akun_dikirim/{uid}_{pid}_x{jumlah}.txt"

    with open(file_path, "w") as f:
        for i, akun in enumerate(akun_terpakai, start=1):
            f.write(
                f"Akun #{i}\n"
                f"Username: {akun['username']}\n"
                f"Password: {akun['password']}\n"
                f"Tipe: {akun['tipe']}\n"
                "------------------------\n"
            )

    with open(file_path, "rb") as f:
        await q.message.reply_document(
            document=f,
            filename=os.path.basename(file_path),
            caption=(f"✅ *Pembelian Berhasil!*\n\n"
                     f"Produk: *{item['nama']}*\n"
                     f"Jumlah: *{jumlah}*\n"
                     f"Total: *Rp{total:,}*"),
            parse_mode="Markdown"
        )

    await send_main_menu(context, q.from_user.id, q.from_user)


# ==========================================================
#                       DEPOSIT MENU
# ==========================================================

async def handle_deposit(update: Update, context: CallbackContext):
    q = update.callback_query

    nominals = [10000, 50000, 100000, 1000000]

    keyboard = [
        [InlineKeyboardButton(f"Rp{n:,}", callback_data=f"deposit_{n}") for n in nominals],
        [InlineKeyboardButton("🔧 Custom Nominal", callback_data="deposit_custom")],
        [InlineKeyboardButton("🔙 Menu Utama", callback_data="main_menu")]
    ]

    await q.edit_message_text(
        "💰 Silakan pilih nominal deposit:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ==========================================================
#                SIMPAN PENDING DEPOSIT
# ==========================================================

def save_pending_deposit(user_id, nominal):
    pending = load_json(deposit_file)
    # Hapus pending non-DONE milik user yang sama
    pending = [
        p for p in pending
        if not (p["user_id"] == user_id and p.get("status") != "DONE")
    ]

    created_at = datetime.now().timestamp()

    pending.append({
        "id": created_at,
        "user_id": user_id,
        "nominal": nominal,
        "total_transfer": nominal + 23,
        "created_at": created_at,
        "status": "WAITING_PROOF",
        "bukti_path": None
    })

    save_json(deposit_file, pending)


# ==========================================================
#                 HANDLE NOMINAL DEPOSIT (NEW)
# ==========================================================

async def handle_deposit_nominal(update: Update, context: CallbackContext):
    q = update.callback_query
    data = q.data
    user = q.from_user
    user_id = user.id

    # Custom nominal -> minta user kirim angka via ReplyKeyboard
    if data == "deposit_custom":
        context.user_data["awaiting_custom"] = True
        keyboard = ReplyKeyboardMarkup(
            [[KeyboardButton("❌ Batalkan Deposit")]],
            resize_keyboard=True
        )
        await q.edit_message_text(
            "🔧 *Custom Nominal*\nKetik nominal deposit (angka saja). Minimal Rp10.000.",
            parse_mode="Markdown"
        )
        return await q.message.reply_text(
            "Silakan ketik nominal sekarang (contoh: 25000).",
            reply_markup=keyboard
        )

    # Fixed nominal: deposit_XXXXX
    try:
        nominal = int(data.split("_")[1])
    except Exception:
        return await q.answer("Nominal tidak valid.", show_alert=True)

    save_pending_deposit(user_id, nominal)

    keyboard = ReplyKeyboardMarkup(
        [
            [KeyboardButton("✅ Kirim Bukti Transfer")],
            [KeyboardButton("❌ Batalkan Deposit")]
        ],
        resize_keyboard=True
    )

    caption = (
        f"💳 *Pembayaran via QRIS*\n\n"
        f"Transfer sebesar: *Rp{nominal + 323:,}*\n"
        "Jika sudah transfer, kirim bukti via tombol di bawah."
    )

    # Edit panel dan kirim instruksi + QRIS di chat
    await q.edit_message_text(
        f"✅ Deposit *Rp{nominal:,}* dibuat. Instruksi pembayaran dikirim ke chat.",
        parse_mode="Markdown"
    )
    if os.path.exists(QRIS_IMAGE_PATH):
        with open(QRIS_IMAGE_PATH, "rb") as f:
            return await q.message.reply_photo(
                photo=f, caption=caption, parse_mode="Markdown", reply_markup=keyboard
            )
    else:
        return await q.message.reply_text(
            caption, parse_mode="Markdown", reply_markup=keyboard
        )


# ==========================================================
#                   HANDLE CANCEL DEPOSIT
# ==========================================================

async def cancel_deposit_full(update, context):
    user_id = update.effective_user.id

    pending = load_json(deposit_file)
    pending = [
        p for p in pending
        if not (p["user_id"] == user_id and p.get("status") != "DONE")
    ]
    save_json(deposit_file, pending)

    context.user_data.pop("awaiting_custom", None)

    await update.message.reply_text(
        "❌ Deposit dibatalkan.",
        reply_markup=ReplyKeyboardRemove()
    )
    await send_main_menu(context, update.effective_chat.id, update.effective_user)


async def handle_cancel_deposit(update: Update, context: CallbackContext):
    q = update.callback_query
    user_id = q.from_user.id

    pending = load_json(deposit_file)
    pending = [
        p for p in pending
        if not (p["user_id"] == user_id and p.get("status") != "DONE")
    ]
    save_json(deposit_file, pending)

    await q.edit_message_text("❌ Deposit dibatalkan.")
    await send_main_menu(context, user_id, q.from_user)


# ==========================================================
#                  HANDLE FOTO (BUKTI TRANSFER)
# ==========================================================

async def handle_photo(update: Update, context: CallbackContext):
    user = update.effective_user
    user_id = user.id

    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)

    os.makedirs("bukti", exist_ok=True)
    bukti_path = f"bukti/{user_id}_{int(datetime.now().timestamp())}.jpg"
    await file.download_to_drive(bukti_path)

    pending = load_json(deposit_file)
    now = datetime.now().timestamp()

    user_pending = [
        p for p in pending
        if p["user_id"] == user_id and p.get("status") != "DONE"
    ]

    if not user_pending:
        return await update.message.reply_text(
            "❌ Tidak ada permintaan deposit aktif.\nSilakan pilih nominal deposit dahulu.",
            parse_mode="Markdown"
        )

    latest = sorted(user_pending, key=lambda x: x["created_at"])[-1]

    nominal = latest["nominal"]
    total_transfer = latest["total_transfer"]
    created_at = latest["created_at"]

    # Batas waktu 10 menit
    if now - created_at > 600:
        pending = [
            p for p in pending
            if not (p["user_id"] == user_id and p["created_at"] == created_at)
        ]
        save_json(deposit_file, pending)

        return await update.message.reply_text(
            "⏰ Waktu deposit sudah lebih dari 10 menit! Silakan buat deposit baru.",
            parse_mode="Markdown"
        )

    # Tandai menunggu admin
    for p in pending:
        if p["user_id"] == user_id and p["created_at"] == created_at:
            p["bukti_path"] = bukti_path
            p["status"] = "WAITING_ADMIN"
            break

    save_json(deposit_file, pending)

    await update.message.reply_text(
        "✅ Bukti transfer diterima.\nMenunggu konfirmasi dari sistem.",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )

    caption_admin = (
        "📥 *Permintaan Deposit Baru*\n\n"
        f"User: {user.full_name} (@{user.username})\n"
        f"ID Telegram: `{user_id}`\n"
        f"ID Deposit: `{int(created_at)}`\n\n"
        f"Total transfer: *Rp{total_transfer:,}*\n"
        f"Saldo masuk: *Rp{nominal:,}*\n"
    )

    keyboard_admin = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✅ Konfirmasi",
                callback_data=f"adm_deposit_ok:{user_id}:{int(created_at)}"
            )
        ],
        [
            InlineKeyboardButton(
                "❌ Tolak",
                callback_data=f"adm_deposit_no:{user_id}:{int(created_at)}"
            )
        ]
    ])

    with open(bukti_path, "rb") as f:
        await context.bot.send_photo(
            chat_id=OWNER_ID,
            photo=InputFile(f),
            caption=caption_admin,
            parse_mode="Markdown",
            reply_markup=keyboard_admin
        )

    await send_main_menu(context, update.effective_chat.id, user)


# ==========================================================
#                     ADMIN DASHBOARD
# ==========================================================

async def handle_admin_panel(update: Update, context: CallbackContext):
    q = update.callback_query
    if q.from_user.id != OWNER_ID:
        return await q.answer("❌ Kamu bukan admin.", show_alert=True)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📦 Kelola Produk", callback_data="admin_produk")],
        [InlineKeyboardButton("📊 Keuangan", callback_data="admin_finance")],
        [InlineKeyboardButton("🧾 Riwayat Transaksi", callback_data="admin_riwayat")],
        [InlineKeyboardButton("💳 Pending Deposit", callback_data="admin_pending")],
        [InlineKeyboardButton("🔙 Kembali", callback_data="main_menu")],
    ])

    await q.edit_message_text(
        "⚙️ *ADMIN PANEL*\nSilakan pilih menu:",
        parse_mode="Markdown",
        reply_markup=keyboard
    )


# ==========================================================
#                   ADMIN – KELOLA PRODUK
# ==========================================================

async def admin_produk(update: Update, context: CallbackContext):
    q = update.callback_query

    produk = load_json(produk_file)
    text = "📦 *KELOLA PRODUK*\n\n"

    if not produk:
        text += "Belum ada produk."

    keyboard = []

    for pid, item in produk.items():
        text += f"• {item['nama']} – Rp{item['harga']:,} – Stok {item['stok']}\n"
        keyboard.append([InlineKeyboardButton(item["nama"], callback_data=f"admin_edit_{pid}")])

    keyboard.append([InlineKeyboardButton("➕ Tambah Produk", callback_data="admin_add_produk")])
    keyboard.append([InlineKeyboardButton("🔙 Kembali", callback_data="admin_panel")])

    await q.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


# ==========================================================
#                      ADMIN – KEUANGAN
# ==========================================================

async def admin_finance(update: Update, context: CallbackContext):
    q = update.callback_query

    statistik = load_json(statistik_file)
    total_transaksi = statistik.get("total_transaksi", 0)
    total_pendapatan = statistik.get("total_pendapatan", 0)

    text = (
        "📊 *PANEL KEUANGAN*\n\n"
        f"• Total Transaksi: *{total_transaksi} kali*\n"
        f"• Total Pendapatan: *Rp{total_pendapatan:,}*\n"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Kembali", callback_data="admin_panel")]
    ])

    await q.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)


# ==========================================================
#                ADMIN – RIWAYAT TRANSAKSI (PAGINATION)
# ==========================================================

async def admin_riwayat(update: Update, context: CallbackContext):
    q = update.callback_query
    data = q.data
    page = 1
    if data.startswith("admin_riwayat_page_"):
        try:
            page = int(data.split("_")[-1])
        except:
            page = 1

    riwayat = load_json(riwayat_file)
    text = "🧾 *RIWAYAT TRANSAKSI*\n\n"

    total = len(riwayat)
    if total == 0:
        text += "Belum ada transaksi."
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Kembali", callback_data="admin_panel")]
        ])
        return await q.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)

    # Urut terbaru dulu
    entries = list(reversed(riwayat))

    total_pages = (total + ADMIN_ITEMS_PER_PAGE - 1) // ADMIN_ITEMS_PER_PAGE or 1
    if page < 1:
        page = 1
    if page > total_pages:
        page = total_pages

    start_idx = (page - 1) * ADMIN_ITEMS_PER_PAGE
    page_entries = entries[start_idx:start_idx + ADMIN_ITEMS_PER_PAGE]

    # Label rentang
    text += f"{label_range(start_idx, len(page_entries), total)}\n\n"

    for r in page_entries:
        text += (
            f"[{r['waktu']}] ID {r['user_id']} "
            f"• {r['jenis']} • Rp{r['jumlah']:,}\n"
        )

    # Navigasi + Kembali
    keyboard_rows = []
    keyboard_rows.append(build_nav_row("admin_riwayat", page, total_pages))
    keyboard_rows.append([InlineKeyboardButton("🔙 Kembali", callback_data="admin_panel")])

    await q.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard_rows))


# ==========================================================
#                  ADMIN – PENDING DEPOSIT (PAGINATION)
# ==========================================================

async def admin_pending(update: Update, context: CallbackContext):
    q = update.callback_query
    data = q.data
    page = 1
    if data.startswith("admin_pending_page_"):
        try:
            page = int(data.split("_")[-1])
        except:
            page = 1

    pending = load_json(deposit_file)
    # Hanya yang belum DONE
    pending = [p for p in pending if p.get("status") != "DONE"]

    text = "💳 *PENDING DEPOSIT*\n\n"

    total = len(pending)
    if total == 0:
        text += "Tidak ada deposit pending."
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Kembali", callback_data="admin_panel")]
        ])
        return await q.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)

    # Urut terbaru dulu (created_at desc)
    pending_sorted = sorted(pending, key=lambda x: x.get("created_at", 0), reverse=True)

    total_pages = (total + ADMIN_ITEMS_PER_PAGE - 1) // ADMIN_ITEMS_PER_PAGE or 1
    if page < 1:
        page = 1
    if page > total_pages:
        page = total_pages

    start_idx = (page - 1) * ADMIN_ITEMS_PER_PAGE
    page_items = pending_sorted[start_idx:start_idx + ADMIN_ITEMS_PER_PAGE]

    text += f"{label_range(start_idx, len(page_items), total)}\n\n"

    keyboard_rows = []

    for p in page_items:
        text += (
            f"• ID: `{int(p['created_at'])}` – User: {p['user_id']}\n"
            f"  Nominal: Rp{p['nominal']:,} | Total Transfer: Rp{p['total_transfer']:,}\n"
            f"  Status: {p.get('status', '-')}\n\n"
        )
        keyboard_rows.append([
            InlineKeyboardButton(
                f"Kelola {p['user_id']}",
                callback_data=f"pending_manage:{p['user_id']}:{int(p['created_at'])}"
            )
        ])

    # Navigasi + Kembali
    keyboard_rows.append(build_nav_row("admin_pending", page, total_pages))
    keyboard_rows.append([InlineKeyboardButton("🔙 Kembali", callback_data="admin_panel")])

    await q.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard_rows))


async def admin_pending_manage(update: Update, context: CallbackContext):
    q = update.callback_query
    _, user_id, dep_id = q.data.split(":")
    user_id = int(user_id)
    dep_id = int(dep_id)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Konfirmasi", callback_data=f"adm_deposit_ok:{user_id}:{dep_id}")],
        [InlineKeyboardButton("❌ Tolak", callback_data=f"adm_deposit_no:{user_id}:{dep_id}")],
        [InlineKeyboardButton("🔙 Kembali", callback_data="admin_pending")]
    ])

    await q.edit_message_text(
        f"Kelola Deposit User ID: {user_id}\nDeposit ID: {dep_id}",
        reply_markup=keyboard
    )


# ==========================================================
#                  ADMIN HANDLER DEPOSIT
# ==========================================================

async def handle_admin_confirm_deposit(update: Update, context: CallbackContext):
    q = update.callback_query

    if q.from_user.id != OWNER_ID:
        return await q.answer("❌ Hanya owner.", show_alert=True)

    _, user_id_str, dep_id_str = q.data.split(":")
    user_id = int(user_id_str)
    dep_id = int(dep_id_str)

    pending = load_json(deposit_file)
    record = None
    for p in pending:
        if p["user_id"] == user_id and int(p["created_at"]) == dep_id:
            record = p
            break

    if not record:
        return await q.answer("Deposit tidak ditemukan.", show_alert=True)

    nominal = record["nominal"]

    saldo = load_json(saldo_file)
    saldo[str(user_id)] = saldo.get(str(user_id), 0) + nominal
    save_json(saldo_file, saldo)

    add_riwayat(user_id, "DEPOSIT", "Deposit masuk", nominal)

    # Hapus dari pending
    pending = [p for p in pending if not (p["user_id"] == user_id and int(p["created_at"]) == dep_id)]
    save_json(deposit_file, pending)

    await context.bot.send_message(
        chat_id=user_id,
        text=(
            f"✅ *Deposit Berhasil!*\n\n"
            f"Saldo bertambah: *Rp{nominal:,}*\n"
            f"Saldo sekarang: *Rp{saldo[str(user_id)]:,}*"
        ),
        parse_mode="Markdown"
    )

    await q.answer("Deposit dikonfirmasi.", show_alert=True)


async def handle_admin_reject_deposit(update: Update, context: CallbackContext):
    q = update.callback_query

    if q.from_user.id != OWNER_ID:
        return await q.answer("❌ Hanya owner.", show_alert=True)

    _, user_id_str, dep_id_str = q.data.split(":")
    user_id = int(user_id_str)
    dep_id = int(dep_id_str)

    pending = load_json(deposit_file)
    pending = [p for p in pending if not (p["user_id"] == user_id and int(p["created_at"]) == dep_id)]
    save_json(deposit_file, pending)

    await context.bot.send_message(
        chat_id=user_id,
        text="❌ *Deposit kamu ditolak admin.*",
        parse_mode="Markdown"
    )

    await q.answer("Deposit ditolak.", show_alert=True)


# ==========================================================
#                       ROUTER CALLBACK
# ==========================================================

async def button_callback(update: Update, context: CallbackContext):
    q = update.callback_query
    data = q.data

    # No-op (indikator halaman)
    if data == "noop":
        return await q.answer()

    # Main menu
    if data == "main_menu":
        return await send_main_menu(context, q.from_user.id, q.from_user)

    # Produk list + pagination
    if data == "list_produk" or data.startswith("list_produk_page_"):
        return await handle_list_produk(update, context)

    # Detail produk by pid
    if data in load_json(produk_file).keys():
        return await handle_produk_detail(update, context)

    # Qty
    if data == "qty_plus":
        return await handle_qty_plus(update, context)
    if data == "qty_minus":
        return await handle_qty_minus(update, context)
    if data == "confirm_order":
        return await handle_confirm_order(update, context)

    # Deposit
    if data == "deposit":
        return await handle_deposit(update, context)
    if data.startswith("deposit_") or data == "deposit_custom":
        return await handle_deposit_nominal(update, context)
    if data == "cancel_deposit":
        return await handle_cancel_deposit(update, context)

    # Admin panel
    if data == "admin_panel":
        return await handle_admin_panel(update, context)
    if data == "admin_produk":
        return await admin_produk(update, context)
    if data == "admin_finance":
        return await admin_finance(update, context)

    # Admin riwayat + pagination
    if data == "admin_riwayat" or data.startswith("admin_riwayat_page_"):
        return await admin_riwayat(update, context)

    # Admin pending + pagination
    if data == "admin_pending" or data.startswith("admin_pending_page_"):
        return await admin_pending(update, context)

    if data.startswith("pending_manage:"):
        return await admin_pending_manage(update, context)

    if data.startswith("adm_deposit_ok:"):
        return await handle_admin_confirm_deposit(update, context)
    if data.startswith("adm_deposit_no:"):
        return await handle_admin_reject_deposit(update, context)

    return await q.answer("Perintah tidak dikenal.")


# ==========================================================
#                    HANDLE TEXT MESSAGE
# ==========================================================

async def handle_text(update: Update, context: CallbackContext):
    text = update.message.text

    if text == "❌ Batalkan Deposit":
        return await cancel_deposit_full(update, context)

    if text == "✅ Kirim Bukti Transfer":
        return await update.message.reply_text("Silakan kirim foto bukti transfer.")

    # Custom nominal flow
    if context.user_data.get("awaiting_custom"):
        if not text.isdigit():
            return await update.message.reply_text("Nominal harus angka!")
        nominal = int(text)
        if nominal < 10000:
            return await update.message.reply_text("Minimal deposit Rp10.000")

        user_id = update.effective_user.id
        save_pending_deposit(user_id, nominal)

        keyboard = ReplyKeyboardMarkup(
            [
                [KeyboardButton("✅ Kirim Bukti Transfer")],
                [KeyboardButton("❌ Batalkan Deposit")]
            ],
            resize_keyboard=True
        )

        caption = (
            f"💳 *Pembayaran via QRIS*\n\n"
            f"Transfer sebesar: *Rp{nominal + 23:,}*\n"
            "Jika sudah transfer, kirim bukti."
        )

        context.user_data["awaiting_custom"] = False

        if os.path.exists(QRIS_IMAGE_PATH):
            with open(QRIS_IMAGE_PATH, "rb") as f:
                return await update.message.reply_photo(
                    photo=f, caption=caption, parse_mode="Markdown", reply_markup=keyboard
                )
        else:
            return await update.message.reply_text(
                caption, parse_mode="Markdown", reply_markup=keyboard
            )

    return await update.message.reply_text("Gunakan tombol menu di bawah.")


# ==========================================================
#                            MAIN
# ==========================================================

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("BOT READY ✓")
    app.run_polling()


if __name__ == "__main__":
    main()
