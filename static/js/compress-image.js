// Utilidad para comprimir imágenes grandes automáticamente
function compressImage(file, maxSizeMB = 1, maxWidthOrHeight = 1920) {
    return new Promise((resolve, reject) => {
        // Si el archivo es SVG, no comprimir
        if (file.type === 'image/svg+xml') {
            resolve(file);
            return;
        }

        const reader = new FileReader();
        reader.readAsDataURL(file);
        
        reader.onload = (event) => {
            const img = new Image();
            img.src = event.target.result;
            
            img.onload = () => {
                const canvas = document.createElement('canvas');
                let width = img.width;
                let height = img.height;

                // Redimensionar si es necesario
                if (width > height) {
                    if (width > maxWidthOrHeight) {
                        height = height * (maxWidthOrHeight / width);
                        width = maxWidthOrHeight;
                    }
                } else {
                    if (height > maxWidthOrHeight) {
                        width = width * (maxWidthOrHeight / height);
                        height = maxWidthOrHeight;
                    }
                }

                canvas.width = width;
                canvas.height = height;

                const ctx = canvas.getContext('2d');
                ctx.drawImage(img, 0, 0, width, height);

                // Comprimir con calidad 0.8
                canvas.toBlob(
                    (blob) => {
                        if (blob) {
                            // Verificar tamaño
                            const sizeMB = blob.size / 1024 / 1024;
                            
                            if (sizeMB > maxSizeMB) {
                                // Si aún es muy grande, reducir más la calidad
                                canvas.toBlob(
                                    (smallerBlob) => {
                                        resolve(new File([smallerBlob], file.name, {
                                            type: file.type,
                                            lastModified: Date.now(),
                                        }));
                                    },
                                    file.type,
                                    0.6
                                );
                            } else {
                                resolve(new File([blob], file.name, {
                                    type: file.type,
                                    lastModified: Date.now(),
                                }));
                            }
                        } else {
                            reject(new Error('Error al comprimir imagen'));
                        }
                    },
                    file.type,
                    0.8
                );
            };
            
            img.onerror = () => reject(new Error('Error al cargar imagen'));
        };
        
        reader.onerror = () => reject(new Error('Error al leer archivo'));
    });
}
