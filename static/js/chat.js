const currentUserId = "{{ session['user_id'] }}";
const currentFirstName = document.getElementById('current-first-name').value;
const currentLastName = document.getElementById('current-last-name').value;
const currentUserName = `${currentFirstName} ${currentLastName}`;
const currentUserEmail = document.getElementById('current-email').value;
let chatUserId = null;

document.getElementById('search-bar').addEventListener('input', async function() {
    const query = this.value;
    const response = await fetch('/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ search_query: query })
    });
    const users = await response.json();
    const chatList = document.getElementById('chat-list');
    chatList.innerHTML = '';
    users.forEach(user => {
        const chatDiv = document.createElement('div');
        chatDiv.className = 'chat';
        chatDiv.textContent = `${user[1]} ${user[2]}`;
        chatDiv.onclick = () => openChat(user[0], `${user[1]} ${user[2]}`);
        chatList.appendChild(chatDiv);
    });
});

document.getElementById('file-input').addEventListener('change', async function(event) {
    const file = event.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);
    formData.append('receiver_id', chatUserId);

    const response = await fetch('/upload_file', {
        method: 'POST',
        body: formData
    });

    const data = await response.json();
    if (data.success) {
        const message = `<a href="/download/${data.file_id}" target="_blank">${file.name}</a>`;
        sendMessage(message, true);
    } else {
        console.error('Error uploading file:', data.error);
    }
});

async function openChat(userId, userName) {
    chatUserId = userId;
    document.getElementById('chat-user-name').textContent = userName;
    const response = await fetch('/get_messages', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chat_user_id: userId })
    });
    const messages = await response.json();
    const messagesDiv = document.getElementById('messages');
    messagesDiv.innerHTML = '';
    messages.forEach(msg => {
        const messageDiv = document.createElement('div');
        messageDiv.className = msg[0] == chatUserId ? 'message received' : 'message sent';
        messageDiv.innerHTML = msg[1]; 
        messagesDiv.appendChild(messageDiv);
    });
}

async function sendMessage(message = null, isFile = false) {
    const messageInput = document.getElementById('message-input');
    if (!message) {
        message = messageInput.value;
    }
    if (!message.trim()) return; 

    await fetch('/send_message', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ receiver_id: chatUserId, message, is_file: isFile })
    });

    messageInput.value = '';
    openChat(chatUserId, document.getElementById('chat-user-name').textContent);
    updateChatList();
}

function handleEnterKey(event) {
    if (event.key === 'Enter') {
        sendMessage();
    }
}

async function updateChatList() {
    const response = await fetch('/get_chat_list');
    const chatListData = await response.json();
    const chatList = document.getElementById('chat-list');
    chatList.innerHTML = '';
    chatListData.forEach(chat => {
        const chatDiv = document.createElement('div');
        chatDiv.className = 'chat';
        chatDiv.textContent = `${chat[1]} ${chat[2]}`;
        chatDiv.onclick = () => openChat(chat[0], `${chat[1]} ${chat[2]}`);
        chatList.appendChild(chatDiv);
    });
}

function toggleUserInfo() {
    const userInfoDiv = document.getElementById('user-info');
    if (userInfoDiv.style.display === 'none' || userInfoDiv.style.display === '') {
        document.getElementById('user-name').textContent = currentUserName;
        document.getElementById('user-email').textContent = currentUserEmail;
        userInfoDiv.style.display = 'block';
    } else {
        userInfoDiv.style.display = 'none';
    }
}

updateChatList();

document.getElementById('message-input').addEventListener('keypress', handleEnterKey);