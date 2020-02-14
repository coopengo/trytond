CREATE SEQUENCE upgrade_version_control_id_seq;

CREATE TABLE upgrade_version_control (
    /* The lock makes sure that this table can have one and only one record */
    Lock char(1) not null,
    current_version VARCHAR,
    constraint PK_T1 PRIMARY KEY (Lock),
    constraint CK_T1_Locked CHECK (Lock='X')
);

INSERT INTO upgrade_version_control (Lock, current_version) VALUES ('X', NULL);
