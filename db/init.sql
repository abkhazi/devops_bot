	create user repl_user with replication encrypted password 'resu';
	select pg_create_physical_replication_slot('replication_slot');
	DROP DATABASE IF EXISTS tg_bot;
	CREATE DATABASE tg_bot;
	\c tg_bot;
	CREATE TABLE Email(ID SERIAL PRIMARY KEY, Email VARCHAR (100) NOT NULL);
    CREATE TABLE PhoneNumbers(ID SERIAL PRIMARY KEY, PhoneNumbers VARCHAR (20) NOT NULL);