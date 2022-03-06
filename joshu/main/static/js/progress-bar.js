var flagDone = 0;       // глобальный флаг, чтобы выключить опрос сервера когда шкала достигнет 100%
jQuery(document).ready(function($){
        show_progress();

        setInterval('show_progress()',1000);   // ms
    });

    function show_progress()
            {
                var url = $("#ProgressBlock").attr("progress-url");  // get the url in "view"
                var pgrbar = $('#progress-bar');
                if (flagDone != 1 ){
                    $.ajax({
                        url: url,
                        cache: false,
                        success: function (data) {
                            // $('#messages_task').html(data.progress.current + ' ' + data.progress.total);
                            var current_lev = (parseFloat(data.progress.current / data.progress.total ).toFixed(1)) * 100;
                            pgrbar.attr('value',current_lev);

                            if (!data.complete) {
                                $('#messages_task').html('Выполнено: ' + current_lev + '%');
                                //pgrbar.css('display', 'inline');
                            }
                            else{
                                $('#messages_task').html('Готово!');
                                flagDone = 1;
                            }

                        },
                        error: function (data) {
                            $('#messages_task').html("Ошибка!");
                        }
                    });
                }
            }
    ;

