package com.demo;

import com.demo.TextUtil;
import org.junit.Assert;
import org.junit.Test;

public class TextUtil_isEmpty_Str_Test_Boundary_33 {


    @Test
    public void isEmpty_ShouldReturnTrue_WhenInputIsNull() {
        Assert.assertTrue(TextUtil.isEmpty(null));
    }

}
