#fxn1
def remove_duplicates(df):

    before = len(df)

    df = df.drop_duplicates()

    removed = before - len(df)

    return df, removed

#fxn2
def drop_empty_columns(df):

    before = len(df.columns)

    df = df.dropna(axis=1, how="all")

    removed = before - len(df.columns)

    return df, removed

#fxn3
def normalize_text(df):

    object_columns = df.select_dtypes(include="object").columns

    for col in object_columns:

        df[col] = (
            df[col]
            .astype(str)
            .str.strip()
            .str.title()
        )

    return df

#Fxn4
def fill_missing(df):

    for col in df.columns:

        if df[col].dtype == "object":

            mode = df[col].mode()

            if not mode.empty:
                df[col] = df[col].fillna(mode.iloc[0])

        else:

            df[col] = df[col].fillna(
                df[col].median()
            )

    return df

#Fxn5 orchester
def clean_dataset(df):

    log = []

    df, removed = remove_duplicates(df)

    log.append(
        f"Removed {removed} duplicate rows."
    )

    df, removed = drop_empty_columns(df)

    log.append(
        f"Dropped {removed} empty columns."
    )

    df = fill_missing(df)

    log.append(
        "Filled missing values."
    )

    df = normalize_text(df)

    log.append(
        "Normalized text columns."
    )

    return df, log