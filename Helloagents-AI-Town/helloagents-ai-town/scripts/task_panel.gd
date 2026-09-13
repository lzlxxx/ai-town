# NPC任务面板
extends CanvasLayer

@onready var panel: Panel = $Panel
@onready var title_label: Label = $Panel/VBox/Header/TitleLabel
@onready var refresh_button: Button = $Panel/VBox/Header/RefreshButton
@onready var close_button: Button = $Panel/VBox/Header/CloseButton
@onready var task_list: VBoxContainer = $Panel/VBox/ScrollContainer/TaskList
@onready var status_label: Label = $Panel/VBox/StatusLabel

var api_client: Node = null
var tasks_cache: Array = []

func _ready() -> void:
	visible = false
	api_client = get_node_or_null("/root/APIClient")

	refresh_button.pressed.connect(_on_refresh_pressed)
	close_button.pressed.connect(_on_close_pressed)

	if api_client:
		api_client.tasks_received.connect(_on_tasks_received)
		api_client.task_accept_result.connect(_on_task_accept_result)
		api_client.task_error.connect(_on_task_error)
	else:
		status_label.text = "API客户端未找到"

	_render_tasks()

func _input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		if event.keycode == KEY_T:
			if _is_text_input_focused():
				return
			toggle_panel()
			get_viewport().set_input_as_handled()

		if visible and event.keycode == KEY_ESCAPE:
			hide_panel()
			get_viewport().set_input_as_handled()

func toggle_panel() -> void:
	if visible:
		hide_panel()
	else:
		show_panel()

func show_panel() -> void:
	visible = true
	_set_player_interacting(true)

	if tasks_cache.is_empty():
		_fetch_tasks()
	else:
		_render_tasks()
		_fetch_tasks()

func hide_panel() -> void:
	visible = false
	_set_player_interacting(false)

func _fetch_tasks() -> void:
	if not api_client:
		status_label.text = "API客户端未找到"
		return

	status_label.text = "任务刷新中..."
	api_client.get_tasks()

func _on_refresh_pressed() -> void:
	_fetch_tasks()

func _on_close_pressed() -> void:
	hide_panel()

func _on_tasks_received(tasks: Array) -> void:
	tasks_cache = tasks
	status_label.text = ""
	_render_tasks()

func _on_task_accept_result(task: Dictionary) -> void:
	_update_cached_task(task)
	status_label.text = "任务已接受"
	_render_tasks()

func _on_task_error(error_message: String) -> void:
	status_label.text = error_message

func _on_accept_task_pressed(task_id: String) -> void:
	if not api_client:
		status_label.text = "API客户端未找到"
		return

	status_label.text = "接受任务中..."
	api_client.accept_task(task_id)

func _on_later_pressed() -> void:
	hide_panel()

func _render_tasks() -> void:
	_clear_task_list()

	if tasks_cache.is_empty():
		var empty_label = _create_label("暂无任务数据", 16, Color(0.7, 0.7, 0.7))
		task_list.add_child(empty_label)
		return

	for task in tasks_cache:
		task_list.add_child(_create_task_card(task))

func _create_task_card(task: Dictionary) -> PanelContainer:
	var card = PanelContainer.new()
	card.size_flags_horizontal = Control.SIZE_EXPAND_FILL

	var box = VBoxContainer.new()
	box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	box.add_theme_constant_override("separation", 6)
	card.add_child(box)

	var header = HBoxContainer.new()
	header.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	box.add_child(header)

	var title = _create_label(str(task.get("title", "未命名任务")), 17, Color(0.95, 0.95, 0.95))
	title.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	header.add_child(title)

	var status = _create_label(_status_text(str(task.get("status", ""))), 14, _status_color(str(task.get("status", ""))))
	header.add_child(status)

	var npc_text = str(task.get("npc_name", "")) + " / " + str(task.get("npc_title", ""))
	box.add_child(_create_label(npc_text, 13, Color(0.68, 0.72, 0.78)))
	box.add_child(_create_label(str(task.get("description", "")), 14, Color(0.86, 0.86, 0.86)))
	box.add_child(_create_label(str(task.get("hint", "")), 13, Color(0.78, 0.82, 0.9)))

	if bool(task.get("can_accept", false)):
		var actions = HBoxContainer.new()
		actions.add_theme_constant_override("separation", 8)
		box.add_child(actions)

		var accept_button = Button.new()
		accept_button.text = "接受"
		accept_button.custom_minimum_size = Vector2(82, 32)
		accept_button.pressed.connect(_on_accept_task_pressed.bind(str(task.get("task_id", ""))))
		actions.add_child(accept_button)

		var later_button = Button.new()
		later_button.text = "暂不接受"
		later_button.custom_minimum_size = Vector2(96, 32)
		later_button.pressed.connect(_on_later_pressed)
		actions.add_child(later_button)

	return card

func _create_label(text_value: String, font_size: int, color: Color) -> Label:
	var label = Label.new()
	label.text = text_value
	label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	label.add_theme_font_size_override("font_size", font_size)
	label.add_theme_color_override("font_color", color)
	return label

func _clear_task_list() -> void:
	for child in task_list.get_children():
		child.queue_free()

func _update_cached_task(task: Dictionary) -> void:
	if task.is_empty():
		return

	var task_id = str(task.get("task_id", ""))
	for index in range(tasks_cache.size()):
		if str(tasks_cache[index].get("task_id", "")) == task_id:
			tasks_cache[index] = task
			return

	tasks_cache.append(task)

func _status_text(status: String) -> String:
	match status:
		"locked":
			return "未解锁"
		"available":
			return "可接受"
		"active":
			return "进行中"
		"completed":
			return "已完成"
		_:
			return status

func _status_color(status: String) -> Color:
	match status:
		"locked":
			return Color(0.58, 0.6, 0.64)
		"available":
			return Color(0.35, 0.78, 0.52)
		"active":
			return Color(0.45, 0.66, 1.0)
		"completed":
			return Color(0.95, 0.72, 0.3)
		_:
			return Color(0.8, 0.8, 0.8)

func _is_text_input_focused() -> bool:
	var focused = get_viewport().gui_get_focus_owner()
	return focused is LineEdit or focused is TextEdit

func _set_player_interacting(is_interacting: bool) -> void:
	var player = get_tree().get_first_node_in_group("player")
	if not player or not player.has_method("set_interacting"):
		return

	if not is_interacting and _is_dialogue_visible():
		return

	player.set_interacting(is_interacting)

func _is_dialogue_visible() -> bool:
	var dialogue_nodes = get_tree().get_nodes_in_group("dialogue_system")
	for node in dialogue_nodes:
		if node.visible:
			return true
	return false
