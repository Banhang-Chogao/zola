"""
LPBank (Ngân hàng TMCP Lộc Phát Việt Nam) PDF statement parser.

Mirrors static/js/l-dashboard/lpbank-parser.js — keep in sync.

Test fixture: tests/fixtures/lpbank/sample-statement.pdf
Expected totals: Debit=12,881,300 · Credit=12,881,300 · Ending Balance=0
"""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SOURCE = "lpbank"
ROOT = Path(__file__).resolve().parent.parent
FIXTURE_PDF = ROOT / "tests" / "fixtures" / "lpbank" / "sample-statement.pdf"

DATE_PATTERN = re.compile(r"^\d{2}/\d{2}/\d{4}$")
ANCHOR_PATTERN = re.compile(
    r"(\d{2}/\d{2}/\d{4})\s+(\d{2}/\d{2}/\d{4}).*?(FT\d{14,})(.*)$"
)
AMOUNT_PATTERN = re.compile(r"\d{1,3}(?:,\d{3})+|\d+")
FT_PATTERN = re.compile(r"FT\d{14,}")

SKIP_LINE_MARKERS = (
    "sao kê tài khoản",
    "bank statement",
    "txn.date",
    "value date",
    "description",
    "txn.no",
    "debit",
    "credit",
    "balance",
    "ngày giao dịch",
    "ngày hiệu lực",
    "nội dung giao dịch",
    "số giao dịch",
    "ghi nợ",
    "ghi có",
    "số dư",
    "đề nghị quý khách",
    "please examine",
    "người ký",
    "ngân hàng thương mại",
    "printing branch",
    "printing time",
    "đơn vị in",
)


@dataclass
class LPBankTransaction:
    txn_date: str
    value_date: str
    description: str
    txn_no: str
    debit: int
    credit: int
    balance: int

    @property
    def amount(self) -> int:
        return self.credit if self.credit else -self.debit

    @property
    def type(self) -> str:
        return "income" if self.credit else "expense"


@dataclass
class LPBankStatement:
    account_name: str = ""
    account_number: str = ""
    customer_name: str = ""
    cif_no: str = ""
    currency: str = "VND"
    from_date: str = ""
    to_date: str = ""
    printing_date: str = ""
    printing_time: str = ""
    opening_balance: int = 0
    ending_balance: int = 0
    total_debit: int = 0
    total_credit: int = 0
    transactions: list[LPBankTransaction] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": SOURCE,
            "account_name": self.account_name,
            "account_number": self.account_number,
            "customer_name": self.customer_name,
            "cif_no": self.cif_no,
            "currency": self.currency,
            "from_date": self.from_date,
            "to_date": self.to_date,
            "printing_date": self.printing_date,
            "printing_time": self.printing_time,
            "opening_balance": self.opening_balance,
            "ending_balance": self.ending_balance,
            "total_debit": self.total_debit,
            "total_credit": self.total_credit,
            "transactions": [
                {
                    "txn_date": t.txn_date,
                    "value_date": t.value_date,
                    "description": t.description,
                    "txn_no": t.txn_no,
                    "debit": t.debit,
                    "credit": t.credit,
                    "balance": t.balance,
                    "amount": t.amount,
                    "type": t.type,
                }
                for t in self.transactions
            ],
        }


def parse_number(value: str | None) -> int:
    if not value:
        return 0
    s = str(value).strip().replace(",", "")
    if not s.isdigit():
        return 0
    return int(s)


def parse_date_to_iso(value: str) -> str:
    m = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", value.strip())
    if not m:
        return value
    dd, mm, yyyy = m.groups()
    return f"{yyyy}-{mm}-{dd}"


def extract_pdf_text(pdf_path: Path) -> str:
    try:
        out = subprocess.run(
            ["pdftotext", "-layout", str(pdf_path), "-"],
            capture_output=True,
            text=True,
            check=True,
        )
        return out.stdout
    except (FileNotFoundError, subprocess.CalledProcessError):
        try:
            import pdfplumber  # type: ignore

            chunks: list[str] = []
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    chunks.append(page.extract_text() or "")
            return "\n".join(chunks)
        except Exception as exc:
            raise RuntimeError("Cần pdftotext hoặc pdfplumber để đọc PDF LPBank") from exc


def _norm_line(line: str) -> str:
    return re.sub(r"\s+", " ", line.strip())


def _should_skip_line(line: str) -> bool:
    low = line.lower()
    return any(m in low for m in SKIP_LINE_MARKERS)


def _is_footer_line(line: str) -> bool:
    low = line.lower()
    return any(
        k in low
        for k in (
            "cộng doanh số",
            "total",
            "số dư cuối kỳ",
            "ending balance",
            "opening balance",
            "số dư đầu kỳ",
        )
    )


def _parse_metadata(text: str, stmt: LPBankStatement) -> None:
    flat = re.sub(r"\s+", " ", text)

    m = re.search(r"Tên tài khoản\s*/\s*Account name:\s*([^/]+?)(?:Mã khách hàng|CIF)", flat, re.I)
    if m:
        stmt.account_name = m.group(1).strip()

    m = re.search(r"Số tài khoản\s*/\s*Account number:\s*(\d+)", flat, re.I)
    if m:
        stmt.account_number = m.group(1).strip()

    m = re.search(r"Tên khách hàng\s*/\s*Customer name:\s*([^/]+?)(?:Địa chỉ|Address)", flat, re.I)
    if m:
        stmt.customer_name = m.group(1).strip()

    m = re.search(r"CIF No:\s*(\d+)", flat, re.I)
    if m:
        stmt.cif_no = m.group(1).strip()

    m = re.search(r"Currency:\s*([A-Z]{3})", flat, re.I)
    if m:
        stmt.currency = m.group(1).strip()

    m = re.search(r"From Date\):\s*(\d{2}/\d{2}/\d{4})", flat, re.I)
    if m:
        stmt.from_date = parse_date_to_iso(m.group(1))

    m = re.search(r"To Date\):\s*(\d{2}/\d{2}/\d{4})", flat, re.I)
    if m:
        stmt.to_date = parse_date_to_iso(m.group(1))

    m = re.search(r"Printing date:\s*(\d{2}/\d{2}/\d{4})", flat, re.I)
    if m:
        stmt.printing_date = parse_date_to_iso(m.group(1))

    m = re.search(r"Printing time:\s*(\d{2}:\d{2})", flat, re.I)
    if m:
        stmt.printing_time = m.group(1).strip()

    for i, raw in enumerate(text.splitlines()):
        low = raw.lower().strip()
        if "opening balance" in low or "số dư đầu kỳ" in low:
            for nxt in text.splitlines()[i : i + 6]:
                lone = _norm_line(nxt)
                if re.fullmatch(r"\d[\d,]*", lone):
                    stmt.opening_balance = parse_number(lone)
                    break
            break

    m = re.search(
        r"Cộng doanh số.*?(\d[\d,]*)\s+(\d[\d,]*).*?Total",
        text,
        re.I | re.S,
    )
    if m:
        stmt.total_debit = parse_number(m.group(1))
        stmt.total_credit = parse_number(m.group(2))

    m = re.search(
        r"Ending Balance\s*(\d[\d,]*)",
        text,
        re.I | re.S,
    )
    if not m:
        m = re.search(r"Số dư cuối kỳ\s*(\d[\d,]*)", text, re.I | re.S)
    if m:
        stmt.ending_balance = parse_number(m.group(1))


def _interpret_amounts(amounts: list[int], prev_balance: int) -> tuple[int, int, int]:
    if not amounts:
        return 0, 0, prev_balance

    if len(amounts) >= 3:
        debit, credit, balance = amounts[-3], amounts[-2], amounts[-1]
        return debit, credit, balance

    balance = amounts[-1]
    txn_amount = amounts[-2] if len(amounts) >= 2 else 0

    if balance > prev_balance:
        return 0, txn_amount, balance
    if balance < prev_balance:
        return txn_amount, 0, balance
    if txn_amount and prev_balance > 0:
        return txn_amount, 0, balance
    if txn_amount:
        return 0, txn_amount, balance
    return 0, 0, balance


def _parse_anchor_line(line: str, prev_balance: int) -> tuple[LPBankTransaction | None, str]:
    m = ANCHOR_PATTERN.search(line)
    if not m:
        return None, ""

    txn_date = parse_date_to_iso(m.group(1))
    value_date = parse_date_to_iso(m.group(2))
    txn_no = m.group(3)
    tail = m.group(4)
    amounts = [parse_number(x) for x in AMOUNT_PATTERN.findall(tail)]
    debit, credit, balance = _interpret_amounts(amounts, prev_balance)

    inline = line[: m.start(3)]
    inline = re.sub(r"^\d{2}/\d{2}/\d{4}\s+\d{2}/\d{2}/\d{4}\s*", "", inline).strip()
    return (
        LPBankTransaction(
            txn_date=txn_date,
            value_date=value_date,
            description=inline,
            txn_no=txn_no,
            debit=debit,
            credit=credit,
            balance=balance,
        ),
        inline,
    )


def parse_lpbank_text(text: str) -> LPBankStatement:
    stmt = LPBankStatement()
    _parse_metadata(text, stmt)

    lines = [_norm_line(ln) for ln in text.splitlines() if ln.strip()]
    prev_balance = stmt.opening_balance
    pending_desc: list[str] = []
    current: LPBankTransaction | None = None

    for line in lines:
        if _should_skip_line(line):
            continue
        if re.fullmatch(r"\d{1,2}", line):
            continue
        if "cộng doanh số" in line.lower():
            if current:
                stmt.transactions.append(current)
                current = None
            break

        if _is_footer_line(line):
            continue

        if ANCHOR_PATTERN.search(line):
            if current:
                extra = " ".join(pending_desc).strip()
                if extra:
                    current.description = (current.description + " " + extra).strip()
                stmt.transactions.append(current)
                prev_balance = current.balance

            current, inline = _parse_anchor_line(line, prev_balance)
            desc_parts = [p for p in pending_desc if p]
            pending_desc = []
            if inline:
                desc_parts.append(inline)
            current.description = " ".join(desc_parts).strip()
            continue

        if FT_PATTERN.search(line) and not ANCHOR_PATTERN.search(line):
            continue

        if DATE_PATTERN.match(line.split()[0] if line.split() else ""):
            continue

        if current is not None:
            pending_desc.append(line.strip())
        elif "opening balance" not in line.lower() and "số dư đầu kỳ" not in line.lower():
            pending_desc.append(line.strip())

    if current:
        extra = " ".join(pending_desc).strip()
        if extra:
            current.description = (current.description + " " + extra).strip()
        stmt.transactions.append(current)

    return stmt


def parse_lpbank_pdf(pdf_path: Path | str) -> LPBankStatement:
    text = extract_pdf_text(Path(pdf_path))
    return parse_lpbank_text(text)


def reconcile(stmt: LPBankStatement) -> dict[str, Any]:
    sum_debit = sum(t.debit for t in stmt.transactions)
    sum_credit = sum(t.credit for t in stmt.transactions)
    ok_debit = stmt.total_debit == 0 or sum_debit == stmt.total_debit
    ok_credit = stmt.total_credit == 0 or sum_credit == stmt.total_credit
    ok_ending = (
        not stmt.transactions
        or stmt.transactions[-1].balance == stmt.ending_balance
    )
    ok = ok_debit and ok_credit and ok_ending
    return {
        "ok": ok,
        "sum_debit": sum_debit,
        "sum_credit": sum_credit,
        "expected_debit": stmt.total_debit,
        "expected_credit": stmt.total_credit,
        "expected_ending": stmt.ending_balance,
        "message": ""
        if ok
        else "Có thể parser chưa đọc đúng định dạng sao kê",
    }


def transactions_for_dashboard(stmt: LPBankStatement) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for t in stmt.transactions:
        rows.append(
            {
                "source": SOURCE,
                "date": f"{t.txn_date}T00:00:00",
                "value_date": t.value_date,
                "description": t.description,
                "txn_no": t.txn_no,
                "debit": t.debit,
                "credit": t.credit,
                "balance": t.balance,
                "amount": t.amount,
                "type": t.type,
            }
        )
    return rows