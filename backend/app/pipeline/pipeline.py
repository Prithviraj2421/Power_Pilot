class Pipeline:

    def __init__(self):

        self.stages = []

    def add_stage(self, stage):

        self.stages.append(stage)

    def execute(self, context):

        for stage in self.stages:

            context = stage.execute(context)

        return context
    
    