// ============= ESTADO GLOBAL =============
const AppState = {
    currentUser: null,
    currentUID: null,
    currentService: null,
    currentAccount: null,
    currentAccountId: null,
    services: {},
    accounts: {},
    selectedImages: []
};

// ============= INICIALIZACIÓN =============
document.addEventListener('DOMContentLoaded', async () => {
    await checkAuth();
    setupEventListeners();
});

// ============= VERIFICACIÓN DE AUTENTICACIÓN =============
async function checkAuth() {
    try {
        const response = await fetch('/api/auth/check');
        const data = await response.json();
        
        if (!data.exists) {
            showScreen('register-screen');
        } else {
            showScreen('login-screen');
        }
    } catch (error) {
        console.error('Error al verificar autenticación:', error);
        showScreen('register-screen');
    }
}

// ============= NAVEGACIÓN ENTRE PANTALLAS =============
function showScreen(screenId) {
    document.querySelectorAll('.screen').forEach(screen => {
        screen.classList.remove('active');
    });
    
    const targetScreen = document.getElementById(screenId);
    if (targetScreen) {
        targetScreen.classList.add('active');
    }
}

function showModal(modalId) {
    console.log('showModal called with:', modalId);
    const modal = document.getElementById(modalId);
    console.log('Modal element found:', modal);
    if (modal) {
        console.log('Adding active class to modal');
        modal.classList.add('active');
        console.log('Active class added, modal classList:', modal.classList);
    } else {
        console.error('Modal with id ' + modalId + ' not found!');
    }
}

function hideModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('closing');
        setTimeout(() => {
            modal.classList.remove('active', 'closing');
        }, 300);
    }
}

function hideAllModals() {
    document.querySelectorAll('.modal').forEach(modal => {
        modal.classList.remove('active');
    });
}

// ============= EVENT LISTENERS =============
function setupEventListeners() {
    // Toggle entre login y registro
    document.getElementById('show-register').addEventListener('click', (e) => {
        e.preventDefault();
        showScreen('register-screen');
    });

    document.getElementById('show-login').addEventListener('click', (e) => {
        e.preventDefault();
        showScreen('login-screen');
    });

    // Login
    document.getElementById('btn-login').addEventListener('click', handleLogin);
    document.getElementById('login-password').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleLogin();
    });

    // Registro
    document.getElementById('btn-register').addEventListener('click', handleRegister);
    document.getElementById('register-email').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleRegister();
    });

    // Navegación
    document.getElementById('back-to-services').addEventListener('click', () => {
        showScreen('services-screen');
        loadServices();
    });

    document.getElementById('back-from-profile').addEventListener('click', () => {
        showScreen('services-screen');
    });

    // Footer de usuario
    document.getElementById('user-footer').addEventListener('click', () => {
        showProfile();
    });

    // Cambiar avatar de perfil
    document.getElementById('profile-avatar').addEventListener('click', () => {
        document.getElementById('profile-avatar-input').click();
    });

    document.getElementById('profile-avatar-input').addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        
        try {
            // Comprimir imagen
            showNotification('Comprimiendo imagen...');
            const compressedFile = await compressImage(file, 1, 1024);
            
            const reader = new FileReader();
            reader.onload = async (event) => {
                const imageData = event.target.result;
                
                // Actualizar UI inmediatamente
                const avatarContainer = document.getElementById('profile-avatar');
                avatarContainer.innerHTML = `
                    <div class="avatar-overlay">
                        <svg width="40" height="40" viewBox="0 0 24 24" fill="none">
                            <path d="M12 4V20M4 12H20" stroke="white" stroke-width="2"/>
                        </svg>
                    </div>
                    <img src="${imageData}" style="width: 100%; height: 100%; object-fit: cover; border-radius: 50%;">
                `;
                
                // Actualizar todos los avatares
                document.querySelectorAll('.user-avatar').forEach(avatar => {
                    avatar.innerHTML = `<img src="${imageData}" style="width: 100%; height: 100%; object-fit: cover; border-radius: 50%;">`;
                });
                
                // Guardar en backend
                const formData = new FormData();
                formData.append('username', AppState.currentUser);
                formData.append('avatar', compressedFile);
                
                const response = await fetch('/api/auth/update-avatar', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                if (data.success) {
                    showNotification('Foto de perfil actualizada');
                } else {
                    showNotification('Error al guardar foto', 'error');
                }
            };
            reader.readAsDataURL(compressedFile);
        } catch (error) {
            console.error('Error:', error);
            showNotification('Error al procesar imagen', 'error');
        }
    });

    // Modales
    document.getElementById('btn-create-service').addEventListener('click', createService);
    document.getElementById('btn-create-account').addEventListener('click', createAccount);
    document.getElementById('btn-close-images').addEventListener('click', () => {
        hideModal('modal-view-images');
    });

    // Botón para cerrar modal de cuenta
    document.getElementById('btn-close-account-modal').addEventListener('click', () => {
        hideModal('modal-view-account');
    });

    // Botones de editar y eliminar cuenta
    document.getElementById('btn-edit-account').addEventListener('click', () => {
        showEditAccountModal();
    });

    document.getElementById('btn-delete-account').addEventListener('click', () => {
        if (confirm('¿Estás seguro de que deseas eliminar esta cuenta?')) {
            deleteAccount();
        }
    });

    document.getElementById('btn-save-changes').addEventListener('click', saveAccountChanges);
    document.getElementById('btn-cancel-edit').addEventListener('click', () => {
        hideModal('modal-edit-account');
        showModal('modal-view-account');
    });

    // Iconos de servicio
    document.getElementById('service-icon-btn').addEventListener('click', () => {
        document.getElementById('service-icon-input').click();
    });

    document.getElementById('service-icon-input').addEventListener('change', (e) => {
        handleIconPreview(e, 'service-icon-preview');
    });

    // Iconos de cuenta
    document.getElementById('account-icon-btn').addEventListener('click', () => {
        document.getElementById('account-icon-input').click();
    });

    document.getElementById('account-icon-input').addEventListener('change', (e) => {
        handleIconPreview(e, 'account-icon-preview');
    });

    // Imágenes de cuenta
    document.getElementById('add-account-image').addEventListener('click', () => {
        document.getElementById('account-images-input').click();
    });

    document.getElementById('account-images-input').addEventListener('change', handleAccountImages);

    // Botón para ver imágenes en cuenta
    document.getElementById('btn-open-images').addEventListener('click', () => {
        hideModal('modal-view-account');
        showModal('modal-view-images');
    });

    // Cambiar password
    document.getElementById('btn-update-password').addEventListener('click', updatePassword);

    // Editar campos de perfil
    document.querySelectorAll('.edit-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const field = e.currentTarget.getAttribute('data-field');
            if (field === 'password') {
                showModal('modal-change-password');
            } else if (field === 'email') {
                const emailInput = document.getElementById('profile-email');
                emailInput.removeAttribute('readonly');
                emailInput.focus();
                emailInput.addEventListener('blur', async () => {
                    await updateEmail(emailInput.value);
                    emailInput.setAttribute('readonly', true);
                }, { once: true });
            }
        });
    });

    // Copiar valores de cuenta
    document.querySelectorAll('.copy-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const field = e.currentTarget.getAttribute('data-copy');
            let value = '';
            
            if (field === 'username') {
                value = document.getElementById('account-view-username').textContent;
            } else if (field === 'password') {
                value = document.getElementById('account-view-password').textContent;
            } else if (field === 'email') {
                value = document.getElementById('account-view-email').textContent;
            }
            
            navigator.clipboard.writeText(value).then(() => {
                showNotification('Copiado al portapapeles');
            });
        });
    });

    // Cerrar modales al hacer click fuera
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                hideModal(modal.id);
            }
        });
    });
}

// ============= MANEJO DE ICONOS E IMÁGENES =============
function handleIconPreview(event, previewId) {
    const file = event.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            const preview = document.getElementById(previewId);
            preview.innerHTML = `<img src="${e.target.result}" alt="Preview">`;
            preview.classList.add('active');
        };
        reader.readAsDataURL(file);
    }
}

function handleAccountImages(event) {
    const files = Array.from(event.target.files);
    AppState.selectedImages = files;
    
    const grid = document.getElementById('account-images-grid');
    
    // Limpiar previsualizaciones anteriores (excepto el botón de agregar)
    grid.querySelectorAll('.image-preview-item').forEach(item => item.remove());
    
    // Agregar nuevas previsualizaciones
    files.forEach((file, index) => {
        const reader = new FileReader();
        reader.onload = (e) => {
            const div = document.createElement('div');
            div.className = 'image-preview-item';
            div.innerHTML = `
                <img src="${e.target.result}" alt="Preview">
                <button class="remove-image" data-index="${index}">×</button>
            `;
            
            div.querySelector('.remove-image').addEventListener('click', () => {
                AppState.selectedImages.splice(index, 1);
                div.remove();
            });
            
            grid.appendChild(div);
        };
        reader.readAsDataURL(file);
    });
}

// ============= AUTENTICACIÓN =============
async function handleLogin() {
    const username = document.getElementById('login-username').value.trim();
    const password = document.getElementById('login-password').value;

    if (!username || !password) {
        showNotification('Por favor completa todos los campos', 'error');
        return;
    }

    try {
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });

        const data = await response.json();

        if (data.success) {
            AppState.currentUser = data.username;
            AppState.currentUID = data.uid;
            
            // Actualizar nombre de usuario en todas las pantallas
            document.querySelectorAll('.user-name').forEach(el => {
                el.textContent = data.username;
            });
            
            document.getElementById('profile-username').textContent = data.username;
            document.getElementById('profile-email').value = data.email;
            document.getElementById('user-uid').textContent = data.uid;
            
            // Cargar avatar si existe
            if (data.avatar) {
                const avatarURL = `/img/${data.avatar}`;
                document.getElementById('profile-avatar').innerHTML = `
                    <div class="avatar-overlay">
                        <svg width="40" height="40" viewBox="0 0 24 24" fill="none">
                            <path d="M12 4V20M4 12H20" stroke="white" stroke-width="2"/>
                        </svg>
                    </div>
                    <img src="${avatarURL}" style="width: 100%; height: 100%; object-fit: cover; border-radius: 50%;">
                `;
                
                document.querySelectorAll('.user-avatar').forEach(avatar => {
                    avatar.innerHTML = `<img src="${avatarURL}" style="width: 100%; height: 100%; object-fit: cover; border-radius: 50%;">`;
                });
            }
            
            showScreen('services-screen');
            await loadServices();
            await updateAccountCount();
            
            // Limpiar campos
            document.getElementById('login-username').value = '';
            document.getElementById('login-password').value = '';
        } else {
            showNotification(data.error || 'Credenciales inválidas', 'error');
        }
    } catch (error) {
        console.error('Error en login:', error);
        showNotification('Error al iniciar sesión', 'error');
    }
}

async function handleRegister() {
    const username = document.getElementById('register-username').value.trim();
    const password = document.getElementById('register-password').value;
    const email = document.getElementById('register-email').value.trim();

    if (!username || !password) {
        showNotification('Usuario y contraseña son requeridos', 'error');
        return;
    }

    try {
        const response = await fetch('/api/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password, email })
        });

        const data = await response.json();

        if (data.success) {
            AppState.currentUser = data.username;
            AppState.currentUID = data.uid;
            
            document.querySelectorAll('.user-name').forEach(el => {
                el.textContent = data.username;
            });
            
            document.getElementById('profile-username').textContent = data.username;
            document.getElementById('profile-email').value = data.email;
            document.getElementById('user-uid').textContent = data.uid;
            
            showScreen('services-screen');
            await loadServices();
            
            // Limpiar campos
            document.getElementById('register-username').value = '';
            document.getElementById('register-password').value = '';
            document.getElementById('register-email').value = '';
            
            showNotification('Cuenta creada exitosamente');
        } else {
            showNotification(data.error || 'Error al crear cuenta', 'error');
        }
    } catch (error) {
        console.error('Error en registro:', error);
        showNotification('Error al registrar usuario', 'error');
    }
}

async function updatePassword() {
    const oldPassword = document.getElementById('current-password').value;
    const newPassword = document.getElementById('new-password').value;

    if (!oldPassword || !newPassword) {
        showNotification('Completa ambos campos', 'error');
        return;
    }

    try {
        const response = await fetch('/api/auth/update-password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                username: AppState.currentUser,
                old_password: oldPassword,
                new_password: newPassword
            })
        });

        const data = await response.json();

        if (data.success) {
            hideModal('modal-change-password');
            showNotification('Contraseña actualizada');
            document.getElementById('current-password').value = '';
            document.getElementById('new-password').value = '';
        } else {
            showNotification(data.error || 'Error al actualizar contraseña', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showNotification('Error al actualizar contraseña', 'error');
    }
}

async function updateEmail(newEmail) {
    try {
        const response = await fetch('/api/auth/update-email', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                username: AppState.currentUser,
                email: newEmail
            })
        });

        const data = await response.json();

        if (data.success) {
            showNotification('Email actualizado');
        } else {
            showNotification(data.error || 'Error al actualizar email', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showNotification('Error al actualizar email', 'error');
    }
}

// ============= SERVICIOS =============
async function loadServices() {
    try {
        const response = await fetch(`/api/services?uid=${AppState.currentUID}`);
        const services = await response.json();
        
        AppState.services = services;
        renderServices(services);
    } catch (error) {
        console.error('Error al cargar servicios:', error);
    }
}

function renderServices(services) {
    const grid = document.getElementById('services-grid');
    grid.innerHTML = '';

    // Botón para agregar servicio
    const addBtn = document.createElement('div');
    addBtn.className = 'grid-item add-item';
    addBtn.innerHTML = '<div class="plus-icon">+</div>';
    addBtn.addEventListener('click', () => {
        showModal('modal-new-service');
        // Limpiar formulario
        document.getElementById('service-name-input').value = '';
        document.getElementById('service-icon-input').value = '';
        document.getElementById('service-icon-preview').innerHTML = '';
        document.getElementById('service-icon-preview').classList.remove('active');
    });
    grid.appendChild(addBtn);

    // Renderizar servicios
    Object.entries(services).forEach(([id, service]) => {
        const item = document.createElement('div');
        item.className = 'grid-item';
        
        let iconHTML = '';
        if (service.icon) {
            iconHTML = `<img src="/img/${service.icon}" alt="${service.name}" class="service-icon">`;
        } else {
            iconHTML = `<div class="service-icon" style="background: #333; border-radius: 8px;"></div>`;
        }
        
        item.innerHTML = `
            ${iconHTML}
            <div class="service-name">${service.name}</div>
        `;
        
        item.addEventListener('click', () => {
            AppState.currentService = id;
            loadAccounts(id, service.name);
        });
        
        grid.appendChild(item);
    });
}

async function createService() {
    const name = document.getElementById('service-name-input').value.trim();
    
    if (!name) {
        showNotification('El nombre es requerido', 'error');
        return;
    }

    const formData = new FormData();
    formData.append('uid', AppState.currentUID);
    formData.append('name', name);
    
    const iconFile = document.getElementById('service-icon-input').files[0];
    if (iconFile) {
        try {
            showNotification('Comprimiendo imagen...');
            const compressedIcon = await compressImage(iconFile, 0.5, 512);
            formData.append('icon', compressedIcon);
        } catch (error) {
            console.error('Error al comprimir:', error);
            formData.append('icon', iconFile);
        }
    }

    try {
        const response = await fetch('/api/services', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.success) {
            hideModal('modal-new-service');
            await loadServices();
            showNotification('Servicio creado');
        } else {
            showNotification(data.error || 'Error al crear servicio', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showNotification('Error al crear servicio', 'error');
    }
}

// ============= CUENTAS =============
async function loadAccounts(serviceId, serviceName) {
    try {
        const response = await fetch(`/api/accounts?service_id=${serviceId}&uid=${AppState.currentUID}`);
        const accounts = await response.json();
        
        AppState.accounts = accounts;
        
        document.getElementById('service-name-display').textContent = serviceName;
        renderAccounts(accounts);
        showScreen('accounts-screen');
    } catch (error) {
        console.error('Error al cargar cuentas:', error);
    }
}

function renderAccounts(accounts) {
    const grid = document.getElementById('accounts-grid');
    grid.innerHTML = '';

    // Botón para agregar cuenta
    const addBtn = document.createElement('div');
    addBtn.className = 'grid-item add-item';
    addBtn.innerHTML = '<div class="plus-icon">+</div>';
    addBtn.addEventListener('click', () => {
        showModal('modal-new-account');
        // Limpiar formulario
        document.getElementById('account-name-input').value = '';
        document.getElementById('account-username-input').value = '';
        document.getElementById('account-password-input').value = '';
        document.getElementById('account-email-input').value = '';
        document.getElementById('account-inicio-servicio').checked = false;
        document.getElementById('account-icon-input').value = '';
        document.getElementById('account-icon-preview').innerHTML = '';
        document.getElementById('account-icon-preview').classList.remove('active');
        document.getElementById('account-images-input').value = '';
        document.getElementById('account-images-grid').querySelectorAll('.image-preview-item').forEach(item => item.remove());
        AppState.selectedImages = [];
    });
    grid.appendChild(addBtn);

    // Renderizar cuentas
    Object.entries(accounts).forEach(([id, account]) => {
        const item = document.createElement('div');
        item.className = 'grid-item';
        
        let iconHTML = '';
        if (account.icon) {
            iconHTML = `<img src="/img/${account.icon}" alt="${account.name}" class="account-icon">`;
        } else {
            iconHTML = `<img src="/img/src/default.svg" alt="${account.name}" class="account-icon">`;
        }
        
        item.innerHTML = `
            ${iconHTML}
            <div class="account-name">${account.name}</div>
        `;
        
        item.addEventListener('click', () => {
            console.log('Clicked account item with id:', id);
            showAccountDetails(id, account);
        });
        
        grid.appendChild(item);
    });
}

async function createAccount() {
    const name = document.getElementById('account-name-input').value.trim();
    const username = document.getElementById('account-username-input').value.trim();
    const password = document.getElementById('account-password-input').value;
    const email = document.getElementById('account-email-input').value.trim();
    const inicioServicio = document.getElementById('account-inicio-servicio').checked;

    if (!username && !email) {
        showNotification('Debes proporcionar usuario o email', 'error');
        return;
    }

    if (!inicioServicio && !password) {
        showNotification('La contraseña es requerida', 'error');
        return;
    }

    const formData = new FormData();
    formData.append('uid', AppState.currentUID);
    formData.append('service_id', AppState.currentService);
    formData.append('name', name);
    formData.append('username', username);
    formData.append('password', password);
    formData.append('email', email);
    formData.append('inicio_servicio', inicioServicio);
    
    const iconFile = document.getElementById('account-icon-input').files[0];
    if (iconFile) {
        try {
            const compressedIcon = await compressImage(iconFile, 0.5, 512);
            formData.append('icon', compressedIcon);
        } catch (error) {
            formData.append('icon', iconFile);
        }
    }
    
    // Comprimir imágenes adicionales
    for (let i = 0; i < AppState.selectedImages.length; i++) {
        try {
            const compressed = await compressImage(AppState.selectedImages[i], 1, 1920);
            formData.append(`image_${i}`, compressed);
        } catch (error) {
            formData.append(`image_${i}`, AppState.selectedImages[i]);
        }
    }

    try {
        const response = await fetch('/api/accounts', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.success) {
            hideModal('modal-new-account');
            await loadAccounts(AppState.currentService, document.getElementById('service-name-display').textContent);
            await updateAccountCount();
            showNotification('Cuenta creada');
        } else {
            showNotification(data.error || 'Error al crear cuenta', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showNotification('Error al crear cuenta', 'error');
    }
}

function showAccountDetails(accountId, account) {
    console.log('showAccountDetails called with:', accountId, account);
    try {
        // Guardar el ID de la cuenta actual
        AppState.currentAccount = account;
        AppState.currentAccountId = accountId;
        console.log('AppState updated, attempting to show modal');
        
        // Mostrar icono
        const iconDisplay = document.getElementById('account-view-icon');
        if (iconDisplay) {
            if (account.icon) {
                iconDisplay.innerHTML = `<img src="/img/${account.icon}" alt="${account.name}" style="width: 120px; height: 120px; object-fit: cover; border-radius: 8px;">`;
            } else {
                iconDisplay.innerHTML = `<img src="/img/src/default.svg" alt="${account.name}" style="width: 120px; height: 120px; object-fit: cover; border-radius: 8px;">`;
            }
        }
        
        // Mostrar datos
        const nameEl = document.getElementById('account-view-name');
        const usernameEl = document.getElementById('account-view-username');
        const passwordEl = document.getElementById('account-view-password');
        const emailEl = document.getElementById('account-view-email');
        const inicioEl = document.getElementById('account-view-inicio');
        
        if (nameEl) nameEl.textContent = account.name;
        if (usernameEl) usernameEl.textContent = account.username || '-';
        if (passwordEl) passwordEl.textContent = account.password || '-';
        if (emailEl) emailEl.textContent = account.email || '-';
        if (inicioEl) inicioEl.textContent = account.inicio_servicio ? 'Sí' : 'No';
        
        // Mostrar botón de imágenes si existen
        const btnOpenImages = document.getElementById('btn-open-images');
        if (account.images && account.images.length > 0) {
            if (btnOpenImages) btnOpenImages.style.display = 'block';
            
            // Cargar imágenes en la galería
            const gallery = document.getElementById('images-gallery');
            if (gallery) {
                gallery.innerHTML = '';
                
                account.images.forEach(imgPath => {
                    const div = document.createElement('div');
                    div.className = 'gallery-image';
                    div.innerHTML = `<img src="/img/${imgPath}" alt="Imagen">`;
                    gallery.appendChild(div);
                });
            }
        } else {
            if (btnOpenImages) btnOpenImages.style.display = 'none';
        }
        
        console.log('About to call showModal for modal-view-account');
        showModal('modal-view-account');
        console.log('showModal called successfully');
    } catch (error) {
        console.error('Error en showAccountDetails:', error);
        showNotification('Error al cargar datos de la cuenta', 'error');
    }
}

function showEditAccountModal() {
    const account = AppState.currentAccount;
    
    // Cargar datos del formulario
    document.getElementById('edit-name-input').value = account.name || '';
    document.getElementById('edit-username-input').value = account.username || '';
    document.getElementById('edit-password-input').value = account.password || '';
    document.getElementById('edit-email-input').value = account.email || '';
    
    hideModal('modal-view-account');
    showModal('modal-edit-account');
}

async function saveAccountChanges() {
    const username = document.getElementById('edit-username-input').value.trim();
    const password = document.getElementById('edit-password-input').value;
    const email = document.getElementById('edit-email-input').value.trim();

    if (!username && !email) {
        showNotification('Debes proporcionar usuario o email', 'error');
        return;
    }

    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);
    formData.append('email', email);

    try {
        const response = await fetch(`/api/accounts/${AppState.currentAccountId}`, {
            method: 'PUT',
            body: formData
        });

        const data = await response.json();

        if (data.success) {
            hideModal('modal-edit-account');
            await loadAccounts(AppState.currentService, document.getElementById('service-name-display').textContent);
            showNotification('Cuenta actualizada');
        } else {
            showNotification(data.error || 'Error al actualizar cuenta', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showNotification('Error al guardar cambios', 'error');
    }
}

async function deleteAccount() {
    try {
        const response = await fetch(`/api/accounts/${AppState.currentAccountId}`, {
            method: 'DELETE'
        });

        const data = await response.json();

        if (data.success) {
            hideModal('modal-view-account');
            await loadAccounts(AppState.currentService, document.getElementById('service-name-display').textContent);
            showNotification('Cuenta eliminada');
        } else {
            showNotification(data.error || 'Error al eliminar cuenta', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showNotification('Error al eliminar cuenta', 'error');
    }
}

// ============= PERFIL =============
function showProfile() {
    showScreen('profile-screen');
}

async function updateAccountCount() {
    try {
        const response = await fetch(`/api/accounts/count?uid=${AppState.currentUID}`);
        const data = await response.json();
        
        document.getElementById('account-count').textContent = data.count;
    } catch (error) {
        console.error('Error al contar cuentas:', error);
    }
}

// ============= NOTIFICACIONES =============
function showNotification(message, type = 'success') {
    // Crear elemento de notificación
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 100px;
        right: 30px;
        background: ${type === 'error' ? '#c42b1c' : '#2a5a2a'};
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 8px;
        box-shadow: 0 5px 20px rgba(0,0,0,0.5);
        z-index: 9999;
        animation: slideInRight 0.3s ease;
    `;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOutRight 0.3s ease';
        setTimeout(() => {
            notification.remove();
        }, 300);
    }, 3000);
}

// Agregar animaciones de notificación
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOutRight {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);
