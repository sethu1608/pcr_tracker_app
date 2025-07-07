CREATE TABLE pcr_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20),
    expiry VARCHAR(20),
    strike_price INT,
    pcr FLOAT,
    timestamp DATETIME
);
