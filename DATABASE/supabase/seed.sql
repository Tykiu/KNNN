-- USERS PROFILE
insert into users (id, name, mssv, email, phone, birth_year, is_tutor, verified, subjects_can_teach)
values
('cd3607dc-b232-43a2-bdf6-2cb9ef33a5bc','Nguyen Van A','2212345','test@gmail.com','0901234567',2003,true,true,'Database');


-- MESSAGES
insert into messages (sender_id, receiver_id, content)
values
('cd3607dc-b232-43a2-bdf6-2cb9ef33a5bc',
 'cd3607dc-b232-43a2-bdf6-2cb9ef33a5bc',
 'Test tin nhan');


-- STUDY BUDDY REQUEST
insert into study_buddy_requests (user_id, number_of_people, subject_id, mode, link_or_address, time, note)
values
('cd3607dc-b232-43a2-bdf6-2cb9ef33a5bc',3,'CTDL','online','https://meet.google.com/test','20:00','On tap truoc ky thi');


-- TUTOR REQUEST
insert into tutor_requests (user_id, subject_id, mode, link_or_address, time, note)
values
('cd3607dc-b232-43a2-bdf6-2cb9ef33a5bc','Database','offline','Thu Duc','18:00','Can gia su database');


-- NOTIFICATIONS
insert into notifications (user_id, content)
values
('cd3607dc-b232-43a2-bdf6-2cb9ef33a5bc','Ban co thong bao moi');