/**
 * Кастомные скрипты интернет-магазина «Твой орех».
 * Включает автоматическое скрытие сообщений (alert) через 4 секунды.
 */

// Дожидаемся полной загрузки DOM
document.addEventListener('DOMContentLoaded', function() {
    // Находим все блоки с классом alert (сообщения об успехе, ошибке и т.д.)
    const alerts = document.querySelectorAll('.alert');

    // Для каждого alert запускаем таймер на автоматическое закрытие
    alerts.forEach(function(alert) {
        setTimeout(function() {
            // Используем Bootstrap-метод для закрытия alert'а
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 4000);   // 4 секунды
    });
});