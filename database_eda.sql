

-- General checks
SELECT TOP 10 * FROM dbo.airline_loyalty_customer_history;

SELECT TOP 10 * FROM dbo.airline_loyalty_flight_activity;


-- check size
SELECT COUNT(*) AS total_customers 
FROM dbo.airline_loyalty_customer_history;


-- Check for missing values
SELECT 
    SUM(CASE WHEN Salary IS NULL THEN 1 ELSE 0 END) AS null_salaries,
    SUM(CASE WHEN Cancellation_Year IS NULL THEN 1 ELSE 0 END) AS active_members,
    COUNT(*) AS total_rows
FROM dbo.airline_loyalty_customer_history;


-- check enrollment types - find promo here probably
SELECT DISTINCT Enrollment_Type 
FROM dbo.airline_loyalty_customer_history;


-- Enrollment by year for trend
SELECT Enrollment_Year, COUNT(*) AS signups
FROM dbo.airline_loyalty_customer_history
GROUP BY Enrollment_Year
ORDER BY Enrollment_Year;


-- Break down 2018 by month 
SELECT Enrollment_Month, COUNT(*) AS signups
FROM dbo.airline_loyalty_customer_history
WHERE Enrollment_Year = 2018
GROUP BY Enrollment_Month
ORDER BY Enrollment_Month;


-- Spikes feb, march, april - find promo period
SELECT Enrollment_Month, Enrollment_Type, COUNT(*) AS signups
FROM dbo.airline_loyalty_customer_history
WHERE Enrollment_Year = 2018 AND Enrollment_Month BETWEEN 1 AND 6
GROUP BY Enrollment_Month, Enrollment_Type
ORDER BY Enrollment_Month;


--Find clv
SELECT 
    MIN(CLV) AS min_clv, 
    MAX(CLV) AS max_clv, 
    AVG(CLV) AS avg_clv
FROM dbo.airline_loyalty_customer_history;


-- Check promo group against standard clv
SELECT Enrollment_Type, AVG(CLV) AS avg_clv, COUNT(*) AS total_members
FROM dbo.airline_loyalty_customer_history
WHERE Enrollment_Year = 2018
GROUP BY Enrollment_Type;


-- Geographic breakdown
SELECT TOP 10 Province, COUNT(*) AS member_count
FROM dbo.airline_loyalty_customer_history
WHERE Enrollment_Type = '2018 Promotion'
GROUP BY Province
ORDER BY member_count DESC;


-- Flights. How many 2018 flights for promo group
SELECT 
    c.Enrollment_Type, 
    SUM(f.Total_Flights) AS total_flights_2018,
    AVG(f.Total_Flights) AS avg_flights_per_member
FROM dbo.airline_loyalty_customer_history c
JOIN dbo.airline_loyalty_flight_activity f ON c.Loyalty_Number = f.Loyalty_Number
WHERE f.Year = 2018
GROUP BY c.Enrollment_Type;


-- How many promo signups flew at last once
SELECT 
    COUNT(DISTINCT c.Loyalty_Number) AS total_promo_members,
    COUNT(DISTINCT f.Loyalty_Number) AS members_who_flew
FROM dbo.airline_loyalty_customer_history c
LEFT JOIN dbo.airline_loyalty_flight_activity f ON c.Loyalty_Number = f.Loyalty_Number
WHERE c.Enrollment_Type = '2018 Promotion';


-- CLV of people enrolled in promo
SELECT SUM(CLV) AS campaign_portfolio_value
FROM dbo.airline_loyalty_customer_history
WHERE Enrollment_Type = '2018 Promotion';


-- Loyalty points 2018 promo group
SELECT SUM(Points_Accumulated) AS total_points_2018
FROM dbo.airline_loyalty_flight_activity f
JOIN dbo.airline_loyalty_customer_history c ON f.Loyalty_Number = c.Loyalty_Number
WHERE c.Enrollment_Type = '2018 Promotion' AND f.Year = 2018;


-- Check education and salary
SELECT Education, AVG(Salary) AS avg_salary, AVG(CLV) AS avg_clv
FROM dbo.airline_loyalty_customer_history
GROUP BY Education
ORDER BY avg_salary DESC;