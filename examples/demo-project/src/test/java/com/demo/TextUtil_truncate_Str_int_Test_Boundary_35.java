package com.demo;

import com.demo.TextUtil;
import org.junit.Assert;
import org.junit.Test;

public class TextUtil_truncate_Str_int_Test_Boundary_35 {


    @Test
    public void truncate_withNullString_returnsNull() {
        String result = TextUtil.truncate(null, 10);
        Assert.assertNull(result);
    }

}
