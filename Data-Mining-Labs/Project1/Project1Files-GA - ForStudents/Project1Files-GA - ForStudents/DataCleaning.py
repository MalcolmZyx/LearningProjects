import pandas as pd
import numpy as np

def clean_excel_data(input_file, output_file):
    print(f"--- Processing {input_file} ---")
    
    try:
        # header=None: First row is data, not labels
        df = pd.read_excel(input_file, header=None)
    except FileNotFoundError:
        print("Error: File not found.")
        return

    # ---------------------------------------------------------
    # RULE 1: Delete row if First Column is empty
    # ---------------------------------------------------------
    # We track the integer index of the first column (which is 0)
    target_col_idx = 0 
    
    initial_rows = len(df)
    df = df.dropna(subset=[target_col_idx])
    print(f"Rule 1: Dropped {initial_rows - len(df)} rows (empty target column).")

    # ---------------------------------------------------------
    # PRE-PROCESSING for Rules 2-5
    # ---------------------------------------------------------
    df_numeric = df.apply(pd.to_numeric, errors='coerce')
    junk_mask = df_numeric.isna()
    zero_mask = (df_numeric == 0)
    combined_mask = junk_mask | zero_mask

    # ---------------------------------------------------------
    # RULES 2, 3, 4: Column Deletion (NO PROTECTION)
    # ---------------------------------------------------------
    cols_to_drop = set()
    total_rows = len(df)
    
    if total_rows > 0:
        for col in df.columns:
            # We are NOT skipping col 0 here per your request.
            # It will be deleted if it is mostly junk/zeros.

            n_junk = junk_mask[col].sum()
            n_zero = zero_mask[col].sum()
            n_combined = combined_mask[col].sum()

            if (n_junk / total_rows) > 0.50:
                cols_to_drop.add(col)
                continue 
            if (n_zero / total_rows) > 0.90:
                cols_to_drop.add(col)
                continue
            if (n_combined / total_rows) > 0.70:
                cols_to_drop.add(col)

    df.drop(columns=list(cols_to_drop), inplace=True)
    print(f"Rules 2-4: Dropped {len(cols_to_drop)} columns.")

    # CRITICAL SAFETY CHECK
    if target_col_idx not in df.columns:
        print("\n!!! CRITICAL ERROR !!!")
        print("The Target Column (Column 1) contained too much junk or zeros and was DELETED.")
        print("Cannot proceed with pIC50 calculation or sorting.")
        return

    # Update mask for Row deletion (Rule 5) by removing dropped columns
    combined_mask = combined_mask.drop(columns=list(cols_to_drop))

    # ---------------------------------------------------------
    # RULE 5: Row Deletion (> 70% junk/zero)
    # ---------------------------------------------------------
    row_bad_pct = combined_mask.mean(axis=1)
    rows_before_rule_5 = len(df)
    df = df[row_bad_pct <= 0.70]
    print(f"Rule 5: Dropped {rows_before_rule_5 - len(df)} rows.")

    # ---------------------------------------------------------
    # RULE 6: Impute Mean for Junk values
    # ---------------------------------------------------------
    print("Rule 6: Imputing means for junk values...")
    for col in df.columns:
        numeric_series = pd.to_numeric(df[col], errors='coerce')
        if numeric_series.notna().sum() > 0:
            mean_val = numeric_series.mean()
            df[col] = numeric_series.fillna(mean_val)

    # =========================================================
    # SCIENTIFIC CALCULATIONS
    # =========================================================
    
    # Ensure all data is strictly numeric (float)
    df = df.apply(pd.to_numeric)

    # ---------------------------------------------------------
    # (1) Target Column Adjustment: pIC50 = -log10(IC50 * 10^-9)
    # ---------------------------------------------------------
    print("Step (1): Converting nM to Molar and calculating pIC50...")
    
    # 1. Convert Nanomolar (300-600) to Molar (3e-7 to 6e-7)
    # Assumption: Input is nM. If input is uM, change 1e-9 to 1e-6.
    df[target_col_idx] = df[target_col_idx] * 1e-9
    
    # 2. Apply -log10
    # We verify we don't take log of 0 or negative numbers
    df[target_col_idx] = df[target_col_idx].apply(lambda x: -np.log10(x) if x > 0 else np.nan)

    # ---------------------------------------------------------
    # (2) Descriptor Rescaling (0-1 range)
    # ---------------------------------------------------------
    print("Step (2): Rescaling descriptors (excluding target)...")
    
    for col in df.columns:
        # SKIP the target column
        if col == target_col_idx:
            continue
        
        min_val = df[col].min()
        max_val = df[col].max()
        
        if max_val == min_val:
            # If max equals min, replacing with 0 (avoid div by zero)
            df[col] = 0.0
        else:
            # Formula: (X - Xmin) / (Xmax - Xmin)
            df[col] = (df[col] - min_val) / (max_val - min_val)

    # ---------------------------------------------------------
    # (3) Sort by pIC50 (High to Low is standard, but using Low to High if preferred)
    # ---------------------------------------------------------
    # Usually, higher pIC50 = more potent. 
    # I will sort Ascending=False (Highest potency at top) as is standard.
    # If you specifically want Low-to-High, change to True.
    print("Step (3): Sorting dataset by pIC50 (Descending/High-to-Low)...")
    df = df.sort_values(by=target_col_idx, ascending=False)

    # ---------------------------------------------------------
    # SAVE
    # ---------------------------------------------------------
    df.to_excel(output_file, index=False, header=False)
    print(f"--- Done. Cleaned & Transformed data saved to {output_file} ---")

if __name__ == "__main__":
    clean_excel_data('Alzheimer2.csv.xlsx', 'cleaned_data.xlsx')