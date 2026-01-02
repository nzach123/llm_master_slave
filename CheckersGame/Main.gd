extends Control

   func _ready():
       var board = Board.new()
       add_child(board)
       var pieces = Pieces.new()
       add_child(pieces)