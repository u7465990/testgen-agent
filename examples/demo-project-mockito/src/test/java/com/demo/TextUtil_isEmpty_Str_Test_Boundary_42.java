package com.demo;

import com.demo.TextUtil;
import org.junit.Assert;
import org.junit.Test;

public class TextUtil_isEmpty_Str_Test_Boundary_42 {


    @Test
    public void testIsEmptyWithNullString() {
        String s = null;
        boolean result = TextUtil.isEmpty(s);
        Assert.assertTrue(result);
    }

}
