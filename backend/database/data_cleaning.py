"""Data cleaning cho 19 file CSV eForms/TED trong raw_data/.

Mỗi hàm clean_<file>() xử lý đúng 1 file CSV độc lập (không merge/join - việc ghép
dữ liệu giữa các file sẽ làm ở bước ETL riêng). Chạy: python data_cleaning.py
"""

import re
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings('ignore', category=RuntimeWarning)
np.seterr(divide='ignore', invalid='ignore', over='ignore')

pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)

BASE_DIR = Path(__file__).resolve().parent
RAW_DIR = BASE_DIR / 'raw_data'
CLEAN_DIR = BASE_DIR / 'clean_data'

# noticeIdentifier/noticeVersion/lotIdentifier phai doc voi dtype=str: neu de pandas
# tu suy luan kieu, gia tri dang chuoi so nhu '01' se bi hieu nham thanh so 1 (mat so 0
# dau), lam sai du lieu khoa dung de join o buoc ETL sau. Dict nay dung an toan cho ca
# 19 file vi pandas tu bo qua cac key khong ton tai trong file dang doc.
KEY_DTYPE = {'noticeIdentifier': str, 'noticeVersion': str, 'lotIdentifier': str}


# --------------------------------------------------------------------------------
# Hàm dùng chung
# --------------------------------------------------------------------------------

def strip_text_columns(df, columns):
    """Loại khoảng trắng thừa ở đầu/cuối cho các cột dạng text; chuỗi rỗng sau khi strip -> NaN."""
    for col in columns:
        df[col] = df[col].astype('string').str.strip()
        df[col] = df[col].replace('', pd.NA)
    return df


def to_bool(series):
    """Chuyển cột dạng chuỗi 'true'/'false' về kiểu boolean có thể NaN (nullable boolean)."""
    mapping = {'true': True, 'false': False}
    return series.astype('string').str.strip().str.lower().map(mapping).astype('boolean')


def to_datetime_col(series):
    """Chuyển cột ngày giờ dạng ISO 8601 (có timezone) về kiểu datetime; giá trị lỗi -> NaT."""
    return pd.to_datetime(series, errors='coerce', utc=True)


def to_numeric_col(series):
    """Chuyển cột dạng số (có thể lẫn khoảng trắng thừa) về kiểu numeric; giá trị lỗi -> NaN."""
    return pd.to_numeric(series.astype('string').str.strip(), errors='coerce')


def drop_missing_keys(df, key_columns, label):
    """Xoá các dòng thiếu giá trị ở cột khoá bắt buộc (vd noticeIdentifier), in số dòng đã loại."""
    n_before = len(df)
    df = df.dropna(subset=key_columns)
    n_after = len(df)
    if n_before != n_after:
        print(f"[{label}] Đã xoá {n_before - n_after} dòng thiếu khoá bắt buộc {key_columns}")
    return df


def load_csv(name):
    fpath = RAW_DIR / f'{name}.csv'
    df = pd.read_csv(fpath, dtype=KEY_DTYPE)
    print(f"Loaded {fpath}: {df.shape}")
    return df


def save_csv(df, name, n_before):
    out_path = CLEAN_DIR / f'{name}_clean.csv'
    df.to_csv(out_path, index=False)
    print(f"Số dòng: trước {n_before} -> sau {len(df)} | Saved to {out_path}\n")
    return {'file': f'{name}.csv', 'rows_before': n_before, 'rows_after': len(df),
            'rows_removed': n_before - len(df)}


# --------------------------------------------------------------------------------
# 1. notice.csv
# --------------------------------------------------------------------------------

def clean_notice():
    df = load_csv('notice')
    n_before = len(df)

    df = df.drop_duplicates()
    # procedureIdentifier la FK tuy chon (~38% thieu) -> khong dua vao khoa bat buoc
    df = drop_missing_keys(df, ['noticeIdentifier', 'noticeVersion'], 'notice')
    df = strip_text_columns(
        df, ['noticeIdentifier', 'noticeVersion', 'procedureIdentifier',
             'procedureLegalBasis', 'formType', 'noticeType']
    )
    df['publicationDate'] = to_datetime_col(df['publicationDate'])

    return save_csv(df, 'notice', n_before)


# --------------------------------------------------------------------------------
# 2. procedure.csv
# --------------------------------------------------------------------------------

def clean_procedure():
    df = load_csv('procedure')
    n_before = len(df)

    df = df.drop_duplicates()
    df = drop_missing_keys(df, ['noticeIdentifier', 'noticeVersion'], 'procedure')
    df = strip_text_columns(
        df, ['noticeIdentifier', 'noticeVersion', 'crossBorderLaw', 'procedureType', 'procedureFeatures']
    )

    df['procedureAccelerated'] = to_bool(df['procedureAccelerated'])
    df['lotsAllRequired'] = to_bool(df['lotsAllRequired'])
    df['lotsMaxAllowed'] = to_numeric_col(df['lotsMaxAllowed']).astype('Int64')
    df['lotsMaxAwarded'] = to_numeric_col(df['lotsMaxAwarded']).astype('Int64')

    return save_csv(df, 'procedure', n_before)


# --------------------------------------------------------------------------------
# 3. purpose.csv
# --------------------------------------------------------------------------------

def clean_purpose():
    df = load_csv('purpose')
    n_before = len(df)

    df = df.drop_duplicates()
    # lotIdentifier rong ~43% co chu dich (dong cap goi thau tong) -> KHONG bat buoc
    df = drop_missing_keys(df, ['noticeIdentifier', 'noticeVersion'], 'purpose')
    df = strip_text_columns(
        df, ['noticeIdentifier', 'noticeVersion', 'lotIdentifier', 'internalIdentifier',
             'mainNature', 'additionalNature', 'title', 'description', 'estimatedValueCurrency']
    )
    df['estimatedValue'] = to_numeric_col(df['estimatedValue'])

    return save_csv(df, 'purpose', n_before)


# --------------------------------------------------------------------------------
# 4. classification.csv
# --------------------------------------------------------------------------------

def clean_classification():
    df = load_csv('classification')
    n_before = len(df)

    df = df.drop_duplicates()
    df = drop_missing_keys(df, ['noticeIdentifier', 'noticeVersion'], 'classification')
    # mainClassificationCode (ma CPV) giu nguyen dang text, khong ep kieu so
    df = strip_text_columns(
        df, ['noticeIdentifier', 'noticeVersion', 'lotIdentifier', 'classificationType',
             'mainClassificationCode', 'additionalClassificationCodes', 'options']
    )

    return save_csv(df, 'classification', n_before)


# --------------------------------------------------------------------------------
# 5. placeOfPerformance.csv
# --------------------------------------------------------------------------------

def _clean_city(value):
    """Chuẩn hoá tên thành phố: bỏ mã bưu điện dính ở đầu, khoảng trắng thừa, viết hoa chữ đầu."""
    if pd.isna(value):
        return pd.NA
    text = str(value).strip()
    text = re.sub(r'^\d{4,5}\s+', '', text).strip()
    text = re.sub(r'\s+', ' ', text)
    if text in ('', '.', '-', 'N/A', 'n/a'):
        return pd.NA
    return text.title()


def clean_place_of_performance():
    df = load_csv('placeOfPerformance')
    n_before = len(df)

    # File nay co dong trung lap hoan toan o du lieu goc -> drop_duplicates xu ly truc tiep
    df = df.drop_duplicates()
    df = drop_missing_keys(df, ['noticeIdentifier', 'noticeVersion'], 'placeOfPerformance')
    df = strip_text_columns(
        df, ['noticeIdentifier', 'noticeVersion', 'lotIdentifier', 'placePerformancePostCode']
    )

    df['placePerformanceCity'] = df['placePerformanceCity'].apply(_clean_city)
    df['placePerformanceCountrySubdivision'] = (
        df['placePerformanceCountrySubdivision'].astype('string').str.strip().str.upper()
    )
    df['placePerformanceCountryCode'] = (
        df['placePerformanceCountryCode'].astype('string').str.strip().str.upper()
    )

    return save_csv(df, 'placeOfPerformance', n_before)


# --------------------------------------------------------------------------------
# 6. duration.csv
# --------------------------------------------------------------------------------

def clean_duration():
    df = load_csv('duration')
    n_before = len(df)

    df = df.drop_duplicates()
    # lotIdentifier o file nay luon bat buoc (moi dong gan voi dung 1 lot cu the)
    df = drop_missing_keys(df, ['noticeIdentifier', 'noticeVersion', 'lotIdentifier'], 'duration')
    df = strip_text_columns(
        df, ['noticeIdentifier', 'noticeVersion', 'lotIdentifier', 'durationPeriodUnit', 'durationOther']
    )

    df['durationPeriodUnit'] = df['durationPeriodUnit'].str.upper()
    df['durationStartDate'] = to_datetime_col(df['durationStartDate'])
    df['durationEndDate'] = to_datetime_col(df['durationEndDate'])
    df['durationPeriod'] = to_numeric_col(df['durationPeriod'])
    df['renewalMaximum'] = to_numeric_col(df['renewalMaximum']).astype('Int64')

    return save_csv(df, 'duration', n_before)


# --------------------------------------------------------------------------------
# 7. submissionTerms.csv
# --------------------------------------------------------------------------------

def clean_submission_terms():
    df = load_csv('submissionTerms')
    n_before = len(df)

    df = df.drop_duplicates()
    df = drop_missing_keys(df, ['noticeIdentifier', 'noticeVersion', 'lotIdentifier'], 'submissionTerms')
    df = strip_text_columns(
        df, ['noticeIdentifier', 'noticeVersion', 'lotIdentifier', 'tenderValidityDeadlineUnit']
    )
    df['tenderValidityDeadlineUnit'] = df['tenderValidityDeadlineUnit'].str.upper()

    df['tenderValidityDeadline'] = to_numeric_col(df['tenderValidityDeadline'])
    df['guaranteeRequired'] = to_bool(df['guaranteeRequired'])
    df['publicOpeningDate'] = to_datetime_col(df['publicOpeningDate'])

    return save_csv(df, 'submissionTerms', n_before)


# --------------------------------------------------------------------------------
# 8. organisation.csv
# --------------------------------------------------------------------------------

def clean_organisation():
    df = load_csv('organisation')
    n_before = len(df)

    df = df.drop_duplicates()
    df = drop_missing_keys(df, ['noticeIdentifier', 'noticeVersion'], 'organisation')
    df = strip_text_columns(
        df,
        ['noticeIdentifier', 'noticeVersion', 'organisationName', 'organisationIdentifier',
         'organisationCity', 'organisationPostCode', 'organisationCountrySubdivision',
         'organisationCountryCode', 'organisationInternetAddress', 'organisationRole',
         'buyerProfileURL', 'buyerLegalType', 'winnerSize', 'winnerOwnerNationality']
    )

    for col in ['organisationCountrySubdivision', 'organisationCountryCode', 'winnerOwnerNationality']:
        df[col] = df[col].str.upper()
    df['winnerSize'] = df['winnerSize'].str.lower()

    df['organisationNaturalPerson'] = to_bool(df['organisationNaturalPerson'])
    df['buyerContractingEntity'] = to_bool(df['buyerContractingEntity'])
    df['winnerListed'] = to_bool(df['winnerListed'])

    return save_csv(df, 'organisation', n_before)


# --------------------------------------------------------------------------------
# 9. lot.csv
# --------------------------------------------------------------------------------

def clean_lot():
    df = load_csv('lot')
    n_before = len(df)

    df = df.drop_duplicates()
    # Ca 3 cot deu la khoa bat buoc o file nay (bang dang ky lot, khong co cot nghiep vu nao khac)
    df = drop_missing_keys(df, ['noticeIdentifier', 'noticeVersion', 'lotIdentifier'], 'lot')
    df = strip_text_columns(df, ['noticeIdentifier', 'noticeVersion', 'lotIdentifier'])

    return save_csv(df, 'lot', n_before)


# --------------------------------------------------------------------------------
# 10. tender.csv
# --------------------------------------------------------------------------------

def clean_tender():
    df = load_csv('tender')
    n_before = len(df)

    df = df.drop_duplicates()
    df = drop_missing_keys(
        df, ['noticeIdentifier', 'noticeVersion', 'tenderIdentifier', 'lotIdentifier'], 'tender'
    )
    df = strip_text_columns(
        df,
        ['noticeIdentifier', 'noticeVersion', 'tenderIdentifier', 'lotIdentifier', 'tenderValueCurrency',
         'tenderPaymentValueCurrency', 'tenderPenaltiesCurrency', 'concessionRevenueUserCurrency',
         'concessionRevenueBuyerCurrency', 'countryOrigin']
    )

    for col in ['tenderValueCurrency', 'tenderPaymentValueCurrency', 'tenderPenaltiesCurrency',
                'concessionRevenueUserCurrency', 'concessionRevenueBuyerCurrency', 'countryOrigin']:
        df[col] = df[col].str.upper()

    for col in ['tenderValue', 'tenderPaymentValue', 'tenderPenalties',
                'concessionRevenueUser', 'concessionRevenueBuyer']:
        df[col] = to_numeric_col(df[col])

    df['tenderRank'] = to_numeric_col(df['tenderRank']).astype('Int64')

    return save_csv(df, 'tender', n_before)


# --------------------------------------------------------------------------------
# 11. contract.csv
# --------------------------------------------------------------------------------

def clean_contract():
    df = load_csv('contract')
    n_before = len(df)

    df = df.drop_duplicates()
    df = drop_missing_keys(df, ['noticeIdentifier', 'noticeVersion', 'contractIdentifier'], 'contract')
    df = strip_text_columns(df, ['noticeIdentifier', 'noticeVersion', 'contractIdentifier'])

    df['winnerDecisionDate'] = to_datetime_col(df['winnerDecisionDate'])
    df['contractConclusionDate'] = to_datetime_col(df['contractConclusionDate'])
    df['contractFrameworkAgreement'] = to_bool(df['contractFrameworkAgreement'])

    return save_csv(df, 'contract', n_before)


# --------------------------------------------------------------------------------
# 12. procedureLotResult.csv
# --------------------------------------------------------------------------------

def clean_procedure_lot_result():
    df = load_csv('procedureLotResult')
    n_before = len(df)

    df = df.drop_duplicates()
    df = drop_missing_keys(
        df, ['noticeIdentifier', 'noticeVersion', 'lotIdentifier', 'procedureLotResultNumber'],
        'procedureLotResult'
    )
    df = strip_text_columns(
        df,
        ['noticeIdentifier', 'noticeVersion', 'lotIdentifier', 'procedureLotResultNumber',
         'winnerChosen', 'notAwardedReason', 'frameworkMaximumValueCurrency',
         'frameworkEstimatedValueCurrency', 'tenderValueLowestCurrency', 'tenderValueHighestCurrency']
    )

    for col in ['frameworkMaximumValueCurrency', 'frameworkEstimatedValueCurrency',
                'tenderValueLowestCurrency', 'tenderValueHighestCurrency']:
        df[col] = df[col].str.upper()

    for col in ['frameworkMaximumValue', 'frameworkEstimatedValue', 'tenderValueLowest', 'tenderValueHighest']:
        df[col] = to_numeric_col(df[col])

    return save_csv(df, 'procedureLotResult', n_before)


# --------------------------------------------------------------------------------
# 13. receivedSubmissions.csv
# --------------------------------------------------------------------------------

def clean_received_submissions():
    df = load_csv('receivedSubmissions')
    n_before = len(df)

    # File nay co dong trung lap hoan toan o du lieu goc -> drop_duplicates xu ly truc tiep
    df = df.drop_duplicates()
    # receivedSubmissionsType thieu la dong tong (breakdown theo loai) -> khong bat buoc
    df = drop_missing_keys(
        df, ['noticeIdentifier', 'noticeVersion', 'procedureLotResultNumber'], 'receivedSubmissions'
    )
    df = strip_text_columns(
        df, ['noticeIdentifier', 'noticeVersion', 'procedureLotResultNumber', 'receivedSubmissionsType']
    )

    df['receivedSubmissionsCount'] = to_numeric_col(df['receivedSubmissionsCount']).astype('Int64')

    return save_csv(df, 'receivedSubmissions', n_before)


# --------------------------------------------------------------------------------
# 14. noticeResult.csv
# --------------------------------------------------------------------------------

def clean_notice_result():
    df = load_csv('noticeResult')
    n_before = len(df)

    df = df.drop_duplicates()
    df = drop_missing_keys(df, ['noticeIdentifier', 'noticeVersion'], 'noticeResult')
    df = strip_text_columns(
        df, ['noticeIdentifier', 'noticeVersion', 'noticeValueCurrency', 'noticeFrameworkValueCurrency']
    )

    df['noticeValueCurrency'] = df['noticeValueCurrency'].str.upper()
    df['noticeFrameworkValueCurrency'] = df['noticeFrameworkValueCurrency'].str.upper()
    df['noticeValue'] = to_numeric_col(df['noticeValue'])
    df['noticeFrameworkValue'] = to_numeric_col(df['noticeFrameworkValue'])

    return save_csv(df, 'noticeResult', n_before)


# --------------------------------------------------------------------------------
# 15. changes.csv
# --------------------------------------------------------------------------------

def clean_changes():
    df = load_csv('changes')
    n_before = len(df)

    df = df.drop_duplicates()
    # contractIdentifier la FK tuy chon (~73% thieu) -> khong bat buoc
    df = drop_missing_keys(
        df, ['noticeIdentifier', 'noticeVersion', 'changeNoticeVersionIdentifier'], 'changes'
    )
    df = strip_text_columns(
        df,
        ['noticeIdentifier', 'noticeVersion', 'contractIdentifier', 'changeNoticeVersionIdentifier',
         'changeReasonCode', 'changeReasonDescription']
    )

    return save_csv(df, 'changes', n_before)


# --------------------------------------------------------------------------------
# 16. secondStage.csv
# --------------------------------------------------------------------------------

def clean_second_stage():
    df = load_csv('secondStage')
    n_before = len(df)

    df = df.drop_duplicates()
    df = drop_missing_keys(df, ['noticeIdentifier', 'noticeVersion', 'lotIdentifier'], 'secondStage')
    df = strip_text_columns(df, ['noticeIdentifier', 'noticeVersion', 'lotIdentifier'])

    df['minimumCandidates'] = to_numeric_col(df['minimumCandidates']).astype('Int64')
    df['maximumCandidatesNumber'] = to_numeric_col(df['maximumCandidatesNumber']).astype('Int64')
    df['maximumCandidatesIndicator'] = to_bool(df['maximumCandidatesIndicator'])
    df['successiveReduction'] = to_bool(df['successiveReduction'])
    df['noNegotiationNecessary'] = to_bool(df['noNegotiationNecessary'])

    return save_csv(df, 'secondStage', n_before)


# --------------------------------------------------------------------------------
# 17. cvdInformation.csv
# --------------------------------------------------------------------------------

def clean_cvd_information():
    df = load_csv('cvdInformation')
    n_before = len(df)

    df = df.drop_duplicates()
    df = drop_missing_keys(
        df, ['noticeIdentifier', 'noticeVersion', 'procedureLotResultNumber'], 'cvdInformation'
    )
    df = strip_text_columns(
        df, ['noticeIdentifier', 'noticeVersion', 'procedureLotResultNumber', 'cvdContractType', 'vehicleCategory']
    )

    df['vehicles'] = to_numeric_col(df['vehicles']).astype('Int64')
    df['zeroEmissionVehicles'] = to_numeric_col(df['zeroEmissionVehicles']).astype('Int64')
    df['cleanVehicles'] = to_numeric_col(df['cleanVehicles']).astype('Int64')

    return save_csv(df, 'cvdInformation', n_before)


# --------------------------------------------------------------------------------
# 18. additionalInformation.csv
# --------------------------------------------------------------------------------

def clean_additional_information():
    df = load_csv('additionalInformation')
    n_before = len(df)

    df = df.drop_duplicates()
    df = drop_missing_keys(df, ['noticeIdentifier', 'noticeVersion', 'lotIdentifier'], 'additionalInformation')
    df = strip_text_columns(df, ['noticeIdentifier', 'noticeVersion', 'lotIdentifier'])

    df['suitableForSMEs'] = to_bool(df['suitableForSMEs'])

    return save_csv(df, 'additionalInformation', n_before)


# --------------------------------------------------------------------------------
# 19. strategicProcurement.csv
# --------------------------------------------------------------------------------

def clean_strategic_procurement():
    df = load_csv('strategicProcurement')
    n_before = len(df)

    df = df.drop_duplicates()
    df = drop_missing_keys(df, ['noticeIdentifier', 'noticeVersion', 'lotIdentifier'], 'strategicProcurement')
    # strategicProcurement co the chua nhieu ma gop boi dau phay (vd 'env-imp,inn-pur') -> giu nguyen
    df = strip_text_columns(
        df,
        ['noticeIdentifier', 'noticeVersion', 'lotIdentifier', 'strategicProcurement',
         'greenProcurementCriteria', 'greenProcurement', 'socialProcurement', 'innovativeProcurement',
         'accessibility', 'cvdContractType']
    )

    df['cleanVehiclesDirective'] = to_bool(df['cleanVehiclesDirective'])

    return save_csv(df, 'strategicProcurement', n_before)


# --------------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------------

CLEANERS = [
    clean_notice, clean_procedure, clean_purpose, clean_classification,
    clean_place_of_performance, clean_duration, clean_submission_terms,
    clean_organisation, clean_lot, clean_tender, clean_contract,
    clean_procedure_lot_result, clean_received_submissions, clean_notice_result,
    clean_changes, clean_second_stage, clean_cvd_information,
    clean_additional_information, clean_strategic_procurement,
]


def main():
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)

    summary_records = [cleaner() for cleaner in CLEANERS]

    summary_df = pd.DataFrame(summary_records)
    summary_df['pct_removed'] = (summary_df['rows_removed'] / summary_df['rows_before'] * 100).round(2)

    print("=== Bảng tóm tắt kết quả làm sạch dữ liệu ===")
    print(summary_df.to_string(index=False))
    print(f"\nTổng số file đã xử lý: {len(summary_df)}")
    print(f"Tổng số dòng trước clean: {summary_df['rows_before'].sum()}")
    print(f"Tổng số dòng sau clean: {summary_df['rows_after'].sum()}")
    print(f"Tổng số dòng đã loại bỏ: {summary_df['rows_removed'].sum()}")

    summary_df.to_csv(CLEAN_DIR / 'summary.csv', index=False)
    print(f"\nSaved summary to {CLEAN_DIR / 'summary.csv'}")


if __name__ == '__main__':
    main()
