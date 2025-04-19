function sendMessage() {
    const messageInput = document.getElementById('userInput');
    const message = messageInput.value.trim();
    
    if (!message) return;
    
    // Disable input while processing
    messageInput.disabled = true;
    
    // Show typing indicator
    showTypingIndicator();
    
    // Add user message to chat
    appendMessage('user', message);
    
    // Clear input
    messageInput.value = '';
    
    // Send to server
    fetch('/chat/send_message', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: message })
    })
    .then(response => response.json())
    .then(data => {
        // Hide typing indicator
        hideTypingIndicator();
        
        if (data.status === 'redirect') {
            // Show completion message if provided
            if (data.message) {
                appendMessage('assistant', data.message);
            }
            
            // Wait a moment before redirecting
            setTimeout(() => {
                // Use the redirect_url from the server directly
                window.location.href = data.redirect_url;
            }, 2000);
        } else if (data.status === 'error') {
            appendMessage('assistant', `Error: ${data.message}`);
        } else {
            appendMessage('assistant', data.message);
        }
        
        // Re-enable input
        messageInput.disabled = false;
        messageInput.focus();
        
        // Scroll to bottom
        scrollToBottom();
    })
    .catch(error => {
        console.error('Error:', error);
        hideTypingIndicator();
        appendMessage('assistant', 'Sorry, there was an error processing your message.');
        messageInput.disabled = false;
        messageInput.focus();
    });
} 