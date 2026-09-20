import pandas as pd
import numpy as np

class DataCleaner:
    def __init__(self, filename):
        # Read the entire file as strings first to accurately detect empty/junk values
        raw = pd.read_csv(filename, header=None, dtype=str)
        # Enforce the expected shape (284 x 989)
        # Use slicing and copy for consistent data frame creation
        self.original = raw.iloc[:284, :989].copy()
            
        print("the data is now inserted into a 2-dimensional array")

    # 1) Delete rows where the first column (dependent variable Y) is empty or contains junk
    def clean_rows_first_column(self):
        # Convert the first column to numeric; junk and empty strings become NaN
        first_col_numeric = pd.to_numeric(self.original.iloc[:, 0], errors="coerce")
        
        # Identify rows where the first column value is NaN (junk or empty)
        junk_or_empty_mask = first_col_numeric.isna()
        
        # Get the original 1-based indices of rows to be deleted
        deleted_idx = (np.where(junk_or_empty_mask)[0] + 1).tolist()
        
        deleted_str = ", ".join(map(str, deleted_idx))
        
        # list indexing for conditional printing
        msg = ("No rows were deleted in the first column check", 
               f"Rows {deleted_str} are deleted")[deleted_str != ""]
        print(msg)
        
        # Keep rows where the first column is NOT junk/empty
        self.cleaned = self.original.loc[~junk_or_empty_mask].copy()

    # 2) Delete columns if more than 50% of the data are either zero or junk
    def clean_columns_zeros_or_junk(self):
        # Convert all data in the current frame to numeric, junk becomes NaN
        numeric = self.cleaned.apply(pd.to_numeric, errors="coerce")
        total_rows = numeric.shape[0] 
        
        # Count the number of zeros and the number of junk (NaN) values per column
        zero_counts = (numeric == 0).sum(axis=0)
        junk_counts = numeric.isna().sum(axis=0)
        
        # Total count of zero OR junk values
        zero_or_junk_counts = zero_counts + junk_counts
        
        # Calculate the fraction of zero or junk
        zero_or_junk_frac = zero_or_junk_counts / total_rows
        
        # Identify columns to drop (fraction > 0.50)
        cols_to_drop = zero_or_junk_frac[zero_or_junk_frac > 0.50].index
        
        # Print 1-based column indices
        cols_print = ", ".join(map(str, (cols_to_drop + 1).tolist()))
        
        # Use list indexing for conditional printing without an if-statement
        msg = ("No columns were deleted", "Columns " + cols_print + " are deleted")[len(cols_to_drop) > 0]
        print(msg)
        
        # Drop the columns from the 'cleaned' DataFrame
        self.cleaned.drop(columns=cols_to_drop, inplace=True)
    
    # 3) Replace remaining junks with the average value of the numerical values in that column
    def replace_junk_with_mean(self):
        # Convert the data to numeric, junk is NaN
        numeric = self.cleaned.apply(pd.to_numeric, errors="coerce")
        
        # Calculate the mean for each column, skipping NaN values (junk)
        col_means = numeric.mean(axis=0, skipna=True)
        
        # Fill NaN values (junk) with the corresponding column mean
        filled = numeric.fillna(col_means)

        # Output for reporting modified positions
        replaced_mask = numeric.isna().values
        modified_positions = np.argwhere(replaced_mask)

        # Map to 1-based indices for rows and columns
        rows = (modified_positions[:, 0] + 1).astype(str)
        # Get the 1-based column index from the current columns list
        cols = (self.cleaned.columns[modified_positions[:, 1]] + 1).astype(str)
        
        # Get the mean values used for replacement
        vals = col_means.iloc[modified_positions[:, 1]].values
        vals_str = np.char.mod("%.4f", vals) # Format mean to 4 decimal places
        
        # Create the output messages
        part = np.char.add("Position (row ", rows)
        part = np.char.add(part, ", col ")
        part = np.char.add(part, cols)
        part = np.char.add(part, ") is modified to ")
        messages = np.char.add(part, vals_str) 

        # list indexing for conditional printing 
        header = ("No cell modifications were necessary", 
                  "The following locations have been modified")[messages.size != 0]
        print(header)
        
        output_messages = messages.tolist()
        print_limit = (messages.size > 10) * 10 or messages.size # Determine print limit
        
        print("\n".join(output_messages[:print_limit]))
        
        print(("\n... and so on for other modified cells.") * (messages.size > 10))

        # Update the cleaned data
        self.cleaned = filled

    # Normalize the data using the required Z-score formula: x' = (x - mu) / sigma
    def normalize_regression_data(self):
        # Convert the cleaned DataFrame to a numpy array for calculation
        data_array = self.cleaned.values.astype(float)
        
        # Calculate the mean (mu) for each column
        mu = np.mean(data_array, axis=0)
        
        # Calculate the population standard deviation (sigma) for each column (ddof=0 for population)
        sigma = np.std(data_array, axis=0, ddof=0)
        
        # Prevent division by zero for columns with no variance (sigma = 0)
        # Use np.where to apply conditional logic without a standard if-statement
        sigma_safe = np.where(sigma == 0, 1.0, sigma)
        
        # Apply the normalization formula
        normalized_array = (data_array - mu) / sigma_safe
        
        # Store the normalized data back into a DataFrame
        self.normalized = pd.DataFrame(normalized_array, 
                                       index=self.cleaned.index, 
                                       columns=self.cleaned.columns)
        print("Data has been normalized using Z-score (Standardization) with population standard deviation.")

    def save_to_excel(self, out_file):
        # Save the original, cleaned, and normalized data to separate sheets
        with pd.ExcelWriter(out_file, engine="openpyxl") as writer:
            self.original.to_excel(writer, sheet_name="Uncleaned", index=False, header=False)
            self.cleaned.to_excel(writer, sheet_name="Cleaned", index=False, header=False)
            self.normalized.to_excel(writer, sheet_name="Normalized", index=False, header=False)
        print(f"Excel file written to {out_file}")


def main():
    # Instantiate the cleaner with the file name
    cleaner = DataCleaner("Alzheimer2.csv") 
    
    # 1) Delete rows where the target value (Col 1) is empty or junk
    cleaner.clean_rows_first_column()
    
    # 2) Delete columns where > 50% of the data is zero or junk
    cleaner.clean_columns_zeros_or_junk()
    
    # 3) Replace remaining junks with the column average
    cleaner.replace_junk_with_mean()
    
    # Normalize the data using the required Z-score formula with population std. dev.
    cleaner.normalize_regression_data()
    
    # Save the results
    cleaner.save_to_excel("Alzheimer_processed.xlsx")

# Execute the main function
main()